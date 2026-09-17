"""Support inbox, the job hold-back delay, and the reordered onboarding flow."""
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.models import Category, SupportMessage, utcnow
from app.db.seed import seed_all
from app.services.access import update_settings
from app.services.jobs import matching_jobs

from tests.conftest import make_job, make_user


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


# --- hold-back delay -------------------------------------------------------
async def test_a_just_uploaded_job_is_held_back_then_released(db, categories):
    await update_settings(db, {"job_delay_minutes": 90})
    user = await make_user(db, category_slugs=["accounts-finance"])

    fresh = await make_job(
        db, categories, category_slug="accounts-finance", title="Fresh Job", created_at=utcnow()
    )
    assert await matching_jobs(db, user, limit=10) == []

    # same job, now older than the hold-back window
    fresh.created_at = utcnow() - timedelta(minutes=91)
    await db.flush()
    assert [j.id for j in await matching_jobs(db, user, limit=10)] == [fresh.id]


async def test_zero_delay_sends_immediately(db, categories):
    await update_settings(db, {"job_delay_minutes": 0})
    user = await make_user(db, category_slugs=["accounts-finance"])
    await make_job(
        db, categories, category_slug="accounts-finance", title="Instant Job", created_at=utcnow()
    )

    assert len(await matching_jobs(db, user, limit=10)) == 1


# --- onboarding order ------------------------------------------------------
async def test_onboarding_asks_job_type_before_categories():
    """The resume step hands off to job types; job types then hands off to categories."""
    import inspect

    from app.bot.handlers import onboarding

    after_details = inspect.getsource(onboarding._after_details)
    on_job_type = inspect.getsource(onboarding.on_job_type)
    on_category_action = inspect.getsource(onboarding.on_category_action)

    assert "_show_job_types" in after_details and "_show_categories" not in after_details
    assert "_show_categories" in on_job_type
    assert "_finish_onboarding" in on_category_action


# --- support inbox ---------------------------------------------------------
async def test_student_message_appears_in_the_inbox_and_reply_reaches_them(
    client, owner_token, engine, monkeypatch
):
    sent: list[tuple[int, str]] = []

    async def fake_safe_send(bot, chat_id, text, markup=None):
        sent.append((chat_id, text))
        return "ok"

    import app.api.admin.support as support_api

    monkeypatch.setattr(support_api, "safe_send", fake_safe_send)
    monkeypatch.setattr(support_api, "get_bot", lambda: object())

    async with _factory(engine)() as s:
        await seed_all(s)
        user = await make_user(s, full_name="Asha Patil")
        s.add(SupportMessage(user_id=user.id, direction="in", text="My resume upload failed"))
        await s.commit()
        user_id = user.id
        telegram_id = user.telegram_id

    h = _auth(owner_token)

    open_threads = (await client.get("/admin/support", params={"status": "open"}, headers=h)).json()
    assert open_threads["total"] == 1
    assert open_threads["items"][0]["full_name"] == "Asha Patil"
    assert open_threads["items"][0]["awaiting_reply"] is True
    assert open_threads["items"][0]["last_message"] == "My resume upload failed"

    reply = await client.post(
        f"/admin/support/{user_id}/reply", json={"text": "Please send it as a PDF"}, headers=h
    )
    assert reply.status_code == 200, reply.text
    assert reply.json()["result"] == "ok"
    assert sent and sent[0][0] == telegram_id and "Please send it as a PDF" in sent[0][1]

    thread = (await client.get(f"/admin/support/{user_id}", headers=h)).json()
    assert [m["direction"] for m in thread["messages"]] == ["in", "out"]

    # answered threads drop out of the open filter but stay in the full list
    assert (await client.get("/admin/support", params={"status": "open"}, headers=h)).json()["total"] == 0
    assert (await client.get("/admin/support", headers=h)).json()["total"] == 1


async def test_bot_support_flow_stores_the_message(db, monkeypatch):
    from app.bot.handlers import support as support_handlers

    user = await make_user(db, status="active", category_slugs=["accounts-finance"])
    answers: list[str] = []

    class _Msg:
        text = "The apply link for job 12 is broken"

        async def answer(self, text, reply_markup=None):
            answers.append(text)

    class _State:
        def __init__(self):
            self.cleared = False

        async def clear(self):
            self.cleared = True

    state = _State()
    await support_handlers.on_support_text(_Msg(), state, db, user)

    stored = (await db.execute(select(SupportMessage).where(SupportMessage.user_id == user.id))).scalars().all()
    assert len(stored) == 1
    assert stored[0].direction == "in"
    assert stored[0].text == "The apply link for job 12 is broken"
    assert state.cleared is True
    assert answers  # the student gets a confirmation


async def test_short_support_message_is_rejected(db):
    from app.bot.handlers import support as support_handlers

    user = await make_user(db)
    answers: list[str] = []

    class _Msg:
        text = "hi"

        async def answer(self, text, reply_markup=None):
            answers.append(text)

    class _State:
        async def clear(self):
            raise AssertionError("state should not be cleared for a rejected message")

    await support_handlers.on_support_text(_Msg(), _State(), db, user)
    assert (await db.execute(select(SupportMessage))).scalars().all() == []
    assert answers


# --- category delivery stats ----------------------------------------------
async def test_category_delivery_stats_show_waiting_students(client, owner_token, engine):
    async with _factory(engine)() as s:
        await seed_all(s)
        await update_settings(s, {"job_delay_minutes": 0})
        categories = {c.slug: c for c in (await s.execute(select(Category))).scalars().all()}
        await make_user(s, full_name="Waiting Student", category_slugs=["accounts-finance"])
        await make_job(s, categories, category_slug="accounts-finance", title="Ready Job")
        await s.commit()

    stats = (await client.get("/admin/categories/delivery-stats", headers=_auth(owner_token))).json()
    row = next(item for item in stats["items"] if item["slug"] == "accounts-finance")
    assert row["jobs"] == 1
    assert row["subscribers"] == 1
    assert row["students_waiting"] == 1
    assert row["sent"] == 0
