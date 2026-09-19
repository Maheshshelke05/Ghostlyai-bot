"""Student app phone login + onboarding (Phase A of the student mobile app)."""
from __future__ import annotations

from app.services.firebase_auth import FirebaseAuthError
from tests.conftest import make_user


def _fake_verify(phone: str):
    async def _verify(id_token: str) -> str:
        return phone

    return _verify


def _fake_verify_raises():
    async def _verify(id_token: str) -> str:
        raise FirebaseAuthError("bad token")

    return _verify


async def test_phone_login_new_user_creates_app_only_account(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.student.auth.verify_phone_token", _fake_verify("+919876500001")
    )

    resp = await client.post("/student/auth/phone", json={"id_token": "whatever-fake-token"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_new_user"] is True
    assert body["next_step"] == "name"
    assert body["user"]["phone"] == "+919876500001"
    assert body["user"]["status"] == "onboarding"
    assert body["access_token"]


async def test_phone_login_existing_telegram_user_is_instant_no_otp_needed(client, db, categories, monkeypatch):
    # Simulate a student who already onboarded via Telegram (has telegram_id, active, categories).
    user = await make_user(
        db, phone="+919876500002", status="active", category_slugs=["it-software"]
    )
    from app.services.access import start_trial

    await start_trial(db, user)
    await db.commit()

    monkeypatch.setattr(
        "app.api.student.auth.verify_phone_token", _fake_verify("+919876500002")
    )

    resp = await client.post("/student/auth/phone", json={"id_token": "whatever-fake-token"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Same Telegram-verified phone -> logged straight in, no separate OTP/verification step.
    assert body["is_new_user"] is False
    assert body["next_step"] == "done"
    assert body["user"]["id"] == user.id
    assert body["user"]["category_ids"] == [c.id for c in [categories["it-software"]]]


async def test_phone_login_invalid_token_is_rejected(client, monkeypatch):
    monkeypatch.setattr("app.api.student.auth.verify_phone_token", _fake_verify_raises())

    resp = await client.post("/student/auth/phone", json={"id_token": "garbage-fake-token"})
    assert resp.status_code == 401


async def test_phone_login_blocked_user_is_refused(client, db, monkeypatch):
    user = await make_user(db, phone="+919876500003", status="blocked")
    await db.commit()

    monkeypatch.setattr(
        "app.api.student.auth.verify_phone_token", _fake_verify("+919876500003")
    )
    resp = await client.post("/student/auth/phone", json={"id_token": "whatever-fake-token"})
    assert resp.status_code == 403


async def _login(client, monkeypatch, phone: str) -> str:
    monkeypatch.setattr("app.api.student.auth.verify_phone_token", _fake_verify(phone))
    resp = await client.post("/student/auth/phone", json={"id_token": "whatever-fake-token"})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


async def test_onboarding_happy_path(client, categories, monkeypatch):
    token = await _login(client, monkeypatch, "+919876500004")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/student/auth/me", headers=headers)
    assert resp.json()["next_step"] == "name"

    resp = await client.put("/student/me/name", json={"full_name": "Rahul Sharma"}, headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["next_step"] == "district"

    resp = await client.put("/student/me/district", json={"district": "aurangabad"}, headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["user"]["district"] == "Chhatrapati Sambhajinagar"  # alias resolved
    assert resp.json()["next_step"] == "profile"

    cat_id = categories["it-software"].id
    resp = await client.post(
        "/student/me/complete",
        json={"category_ids": [cat_id], "job_types": ["private", "wfh"]},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["next_step"] == "done"
    assert body["user"]["status"] == "active"
    assert body["user"]["category_ids"] == [cat_id]
    assert body["user"]["job_types"] == ["private", "wfh"]


async def test_complete_onboarding_rejects_bad_name_before_reaching_here(client, monkeypatch):
    token = await _login(client, monkeypatch, "+919876500005")
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.put("/student/me/name", json={"full_name": "Solo"}, headers=headers)
    assert resp.status_code == 400  # valid_name() requires first + last name


async def test_complete_onboarding_requires_name_and_district_first(client, monkeypatch):
    token = await _login(client, monkeypatch, "+919876500006")
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post(
        "/student/me/complete", json={"category_ids": [1], "job_types": []}, headers=headers
    )
    assert resp.status_code == 400


async def test_complete_onboarding_enforces_max_categories(client, categories, monkeypatch):
    token = await _login(client, monkeypatch, "+919876500007")
    headers = {"Authorization": f"Bearer {token}"}
    await client.put("/student/me/name", json={"full_name": "Anita Patil"}, headers=headers)
    await client.put("/student/me/district", json={"district": "Pune"}, headers=headers)

    all_ids = [c.id for c in categories.values()][:4]  # max_categories default is 3
    resp = await client.post(
        "/student/me/complete", json={"category_ids": all_ids, "job_types": []}, headers=headers
    )
    assert resp.status_code == 400
    assert "Pick 1 to 3" in resp.json()["detail"]


async def test_complete_onboarding_rejects_invalid_category_and_job_type(client, categories, monkeypatch):
    token = await _login(client, monkeypatch, "+919876500008")
    headers = {"Authorization": f"Bearer {token}"}
    await client.put("/student/me/name", json={"full_name": "Anita Patil"}, headers=headers)
    await client.put("/student/me/district", json={"district": "Pune"}, headers=headers)

    resp = await client.post(
        "/student/me/complete", json={"category_ids": [999999], "job_types": []}, headers=headers
    )
    assert resp.status_code == 400

    valid_id = categories["it-software"].id
    resp = await client.post(
        "/student/me/complete", json={"category_ids": [valid_id], "job_types": ["not-a-type"]}, headers=headers
    )
    assert resp.status_code == 400


async def test_push_token_set_and_clear(client, monkeypatch):
    token = await _login(client, monkeypatch, "+919876500009")
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.put("/student/me/push-token", json={"token": "ExponentPushToken[abc]"}, headers=headers)
    assert resp.status_code == 200
    resp = await client.put("/student/me/push-token", json={"token": None}, headers=headers)
    assert resp.status_code == 200


async def test_unauthenticated_request_is_rejected(client):
    resp = await client.get("/student/auth/me")
    assert resp.status_code == 401
    resp = await client.put("/student/me/name", json={"full_name": "X Y"})
    assert resp.status_code == 401


async def test_admin_token_cannot_be_used_as_student_token(client, owner_token):
    resp = await client.get("/student/auth/me", headers={"Authorization": f"Bearer {owner_token}"})
    assert resp.status_code == 401


async def test_public_meta_endpoints(client, categories):
    resp = await client.get("/student/categories")
    assert resp.status_code == 200
    assert len(resp.json()) == len(categories)

    resp = await client.get("/student/districts")
    assert resp.status_code == 200
    assert "Pune" in resp.json()["districts"]

    resp = await client.get("/student/settings")
    assert resp.status_code == 200
    assert resp.json()["price_inr"] == 99
