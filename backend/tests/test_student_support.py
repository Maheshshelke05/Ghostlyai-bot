"""Phase D: student app support thread (POST/GET /student/support), and the admin reply
endpoint's new push-notification path for app-connected students."""
from __future__ import annotations

from sqlalchemy import select

from app.db.models import SupportMessage
from app.services.auth import create_token

from tests.conftest import make_user


async def _student_headers(user) -> dict:
    token = create_token(user.id, "student")
    return {"Authorization": f"Bearer {token}"}


async def test_send_and_read_support_thread(client, db):
    user = await make_user(db)
    await db.commit()
    headers = await _student_headers(user)

    resp = await client.post("/student/support", data={"text": "My apply link is broken"}, headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["direction"] == "in"

    resp = await client.get("/student/support", headers=headers)
    assert resp.status_code == 200
    messages = resp.json()["messages"]
    assert len(messages) == 1
    assert messages[0]["text"] == "My apply link is broken"
    assert messages[0]["image_url"] is None


async def test_send_support_message_with_subject_and_image(client, db, monkeypatch, tmp_path):
    user = await make_user(db)
    await db.commit()
    headers = await _student_headers(user)

    # Real Cloudinary credentials may be configured in this dev environment (same as the
    # resume-upload tests deal with) - mock the actual upload so this test never makes a real
    # network call, same pattern as tests/test_student_auth.py's _fake_save_resume.
    saved_path = str(tmp_path / "support_image.png")

    async def _fake_save_support_image(message_id, data, mime):
        with open(saved_path, "wb") as f:
            f.write(data)
        return saved_path

    async def _fake_get_support_image_url(path):
        return None

    import app.api.student.support as student_support_module

    monkeypatch.setattr(student_support_module, "save_support_image", _fake_save_support_image)
    monkeypatch.setattr(student_support_module, "get_support_image_url", _fake_get_support_image_url)

    resp = await client.post(
        "/student/support",
        data={"text": "Screenshot attached", "subject": "Payment issue"},
        files={"image": ("proof.png", b"\x89PNG\r\n\x1a\n" + b"0" * 20, "image/png")},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["subject"] == "Payment issue"
    assert body["image_url"] == f"/student/support/{body['id']}/image"

    resp = await client.get(f"/student/support/{body['id']}/image", headers=headers)
    assert resp.status_code == 200
    assert resp.content.startswith(b"\x89PNG")


async def test_support_rejects_unsupported_image_type(client, db):
    user = await make_user(db)
    await db.commit()
    resp = await client.post(
        "/student/support",
        data={"text": "Here is a file"},
        files={"image": ("virus.exe", b"not an image", "application/octet-stream")},
        headers=await _student_headers(user),
    )
    assert resp.status_code == 400


async def test_support_message_too_short_is_rejected(client, db):
    user = await make_user(db)
    await db.commit()
    resp = await client.post("/student/support", data={"text": "hi"}, headers=await _student_headers(user))
    assert resp.status_code == 422


async def test_support_requires_auth(client):
    resp = await client.post("/student/support", data={"text": "hello there"})
    assert resp.status_code == 401
    resp = await client.get("/student/support")
    assert resp.status_code == 401


async def test_admin_reply_pushes_app_only_student_without_crashing(client, db, owner_token, monkeypatch):
    """An app-only student has telegram_id=None - the reply endpoint's Telegram send must
    degrade to a harmless "skipped" (not crash, not mark bot_blocked) and still push."""
    student = await make_user(db, telegram_id=None, status="active")
    student.expo_push_token = "ExponentPushToken[abc]"
    await db.commit()

    push_calls = []

    async def fake_send_push_to_student(user, title, body, data=None):
        push_calls.append((user.id, title, body))

    import app.api.admin.support as admin_support_module

    monkeypatch.setattr(admin_support_module, "send_push_to_student", fake_send_push_to_student)
    # get_bot() constructs a real aiogram Bot(token=settings.BOT_TOKEN), which validates the
    # token format at construction time - CI has no real BOT_TOKEN configured. chat_id is None
    # here so safe_send() never actually touches the bot object, but it still evaluates
    # get_bot() as an argument first, so it must not raise. Same pattern as
    # test_support_and_delay.py's test_student_message_appears_in_the_inbox_and_reply_reaches_them.
    monkeypatch.setattr(admin_support_module, "get_bot", lambda: object())

    resp = await client.post(
        f"/admin/support/{student.id}/reply",
        json={"text": "We fixed the apply link, please try again"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert resp.status_code == 200, resp.text
    assert resp.json()["result"] == "skipped"
    assert student.status == "active"  # never incorrectly marked bot_blocked

    assert push_calls == [(student.id, "Support replied", "We fixed the apply link, please try again")]

    refreshed = (
        await db.execute(select(SupportMessage).where(SupportMessage.user_id == student.id))
    ).scalar_one()
    assert refreshed.direction == "out"
