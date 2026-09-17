"""End-to-end run with a crowd of fake students: the real digest worker, real matching,
real delivery bookkeeping, only the Telegram transport faked.

Checks the guarantees the product depends on:
- every eligible student gets each matching job exactly once
- a second digest run sends nothing new (no duplicates, ever)
- jobs inside the hold-back window are not sent yet, and go out once released
- job-type and category preferences are respected
- blocked / onboarding / no-access students get no job messages
- finishing onboarding sends the immediate digest and the scheduled run doesn't repeat it
"""
from contextlib import asynccontextmanager
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.models import Category, JobDelivery, User, utcnow
from app.db.seed import seed_all
from app.services.access import update_settings
from app.workers import digest as digest_worker

from tests.conftest import FakeBot, make_job, make_user


def _job_titles_sent_to(bot: FakeBot, telegram_id: int) -> list[str]:
    """Job titles are the 'N. Title' line of each digest message; a message can hold up to 5 jobs."""
    titles: list[str] = []
    for m in bot.sent:
        if m["chat_id"] != telegram_id:
            continue
        for line in m["text"].split("\n"):
            if line[:1].isdigit() and ". " in line[:4]:
                titles.append(line.split(". ", 1)[1].strip())
    return titles


async def test_digest_across_a_crowd_of_fake_students(engine, monkeypatch):
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)

    @asynccontextmanager
    async def scope():
        async with factory() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    bot = FakeBot()
    monkeypatch.setattr(digest_worker, "session_scope", scope)
    monkeypatch.setattr(digest_worker, "get_bot", lambda: bot)

    now = utcnow()
    async with factory() as s:
        await seed_all(s)
        await update_settings(s, {"job_delay_minutes": 90, "digest_max_jobs": 10})
        cats = {c.slug: c for c in (await s.execute(select(Category))).scalars().all()}

        # --- students ---------------------------------------------------------
        accounts = [await make_user(s, full_name=f"Accounts Student {i}", category_slugs=["accounts-finance"],
                                    trial_ends_at=now + timedelta(days=2)) for i in range(8)]
        it_paid = [await make_user(s, full_name=f"IT Student {i}", category_slugs=["it-software"],
                                   paid_until=now + timedelta(days=20)) for i in range(6)]
        govt_only = [await make_user(s, full_name=f"Govt Only {i}", category_slugs=["accounts-finance"],
                                     job_types=["govt"], trial_ends_at=now + timedelta(days=2)) for i in range(3)]
        both_cats = await make_user(s, full_name="Both Cats", category_slugs=["accounts-finance", "it-software"],
                                    trial_ends_at=now + timedelta(days=2))
        expired = [await make_user(s, full_name=f"Expired {i}", category_slugs=["accounts-finance"],
                                   trial_ends_at=now - timedelta(days=3)) for i in range(3)]
        banned = await make_user(s, full_name="Banned", status="blocked", category_slugs=["accounts-finance"],
                                 trial_ends_at=now + timedelta(days=2))
        still_onboarding = await make_user(s, full_name="Onboarding", status="onboarding",
                                           category_slugs=["accounts-finance"])
        bot_gone = await make_user(s, full_name="Blocks The Bot", category_slugs=["accounts-finance"],
                                   trial_ends_at=now + timedelta(days=2))
        bot.forbidden_chat_ids.add(bot_gone.telegram_id)

        # --- jobs --------------------------------------------------------------
        ready_acc = [await make_job(s, cats, category_slug="accounts-finance", title=f"Accounts Job {i}",
                                    job_type="private") for i in range(3)]
        ready_acc_govt = await make_job(s, cats, category_slug="accounts-finance", title="Accounts Govt Job", job_type="govt")
        ready_it = [await make_job(s, cats, category_slug="it-software", title=f"IT Job {i}", job_type="wfh") for i in range(2)]
        held = await make_job(s, cats, category_slug="accounts-finance", title="Held Fresh Job", created_at=now)
        await make_job(s, cats, category_slug="accounts-finance", title="Expired Deadline Job",
                       last_date=(now - timedelta(days=1)).date())
        await make_job(s, cats, category_slug="accounts-finance", title="Ancient Job", created_at=now - timedelta(days=9))
        await make_job(s, cats, category_slug="banking", title="Banking Job Nobody Wants")
        await s.commit()

    # --- first scheduled run ----------------------------------------------------
    await digest_worker.run_digest()

    acc_expected = sorted(j.title for j in ready_acc) + ["Accounts Govt Job"]
    for u in accounts:
        assert sorted(_job_titles_sent_to(bot, u.telegram_id)) == sorted(acc_expected), u.full_name
    for u in it_paid:
        assert sorted(_job_titles_sent_to(bot, u.telegram_id)) == sorted(j.title for j in ready_it), u.full_name
    for u in govt_only:
        assert _job_titles_sent_to(bot, u.telegram_id) == ["Accounts Govt Job"], u.full_name
    assert sorted(_job_titles_sent_to(bot, both_cats.telegram_id)) == sorted(acc_expected + [j.title for j in ready_it])

    for u in expired:
        titles = _job_titles_sent_to(bot, u.telegram_id)
        assert titles == [], "expired students must not receive job lines"
        teasers = [m for m in bot.sent if m["chat_id"] == u.telegram_id]
        assert len(teasers) == 1, "expired students get exactly one locked teaser"
    assert not [m for m in bot.sent if m["chat_id"] == banned.telegram_id]
    assert not [m for m in bot.sent if m["chat_id"] == still_onboarding.telegram_id]

    everything_sent = [t for m in bot.sent for t in [m["text"]]]
    assert not any("Held Fresh Job" in t for t in everything_sent)
    assert not any("Expired Deadline Job" in t for t in everything_sent)
    assert not any("Ancient Job" in t for t in everything_sent)
    assert not any("Banking Job Nobody Wants" in t for t in everything_sent)

    async with factory() as s:
        gone = await s.get(User, bot_gone.id)
        assert gone.status == "bot_blocked"
        # delivery rows: one per (job, user), never more
        dup = (await s.execute(
            select(JobDelivery.job_id, JobDelivery.user_id, func.count())
            .group_by(JobDelivery.job_id, JobDelivery.user_id)
            .having(func.count() > 1)
        )).all()
        assert dup == []
        assert (await s.execute(select(func.count(JobDelivery.id)).where(JobDelivery.user_id == gone.id))).scalar_one() == 0, \
            "a student who blocked the bot must have no delivery rows, so they get the jobs if they come back"

    # --- second run: nothing new ------------------------------------------------
    before = len(bot.sent)
    await digest_worker.run_digest()
    assert len(bot.sent) == before, "re-running the digest must not resend anything"

    # --- the held job is released once it clears the window ------------------
    async with factory() as s:
        row = await s.get(type(held), held.id)
        row.created_at = now - timedelta(minutes=95)
        await s.commit()
    await digest_worker.run_digest()
    for u in accounts + [both_cats]:
        assert _job_titles_sent_to(bot, u.telegram_id).count("Held Fresh Job") == 1, u.full_name
    for u in govt_only + it_paid:
        assert "Held Fresh Job" not in _job_titles_sent_to(bot, u.telegram_id), u.full_name

    # --- and running yet again still sends nothing ----------------------------
    before = len(bot.sent)
    await digest_worker.run_digest()
    assert len(bot.sent) == before


async def test_finishing_onboarding_sends_once_and_scheduled_run_does_not_repeat(engine, monkeypatch):
    from app.bot.handlers import onboarding

    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)

    @asynccontextmanager
    async def scope():
        async with factory() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    bot = FakeBot()
    monkeypatch.setattr(digest_worker, "session_scope", scope)
    monkeypatch.setattr(digest_worker, "get_bot", lambda: bot)

    async with factory() as s:
        await seed_all(s)
        await update_settings(s, {"job_delay_minutes": 90})
        cats = {c.slug: c for c in (await s.execute(select(Category))).scalars().all()}
        student = await make_user(s, full_name="New Student", status="onboarding", trial_ends_at=None)
        acc = cats["accounts-finance"]
        await make_job(s, cats, category_slug="accounts-finance", title="Ready Before Signup")
        await make_job(s, cats, category_slug="accounts-finance", title="Held At Signup", created_at=utcnow())
        await s.commit()

        class _Msg:
            def __init__(self):
                self.bot = bot
                self.answers = []

            async def answer(self, text, reply_markup=None):
                self.answers.append(text)

        class _State:
            def __init__(self, data):
                self._data = data

            async def get_data(self):
                return self._data

            async def clear(self):
                self._data = {}

        msg = _Msg()
        state = _State({"selected_category_ids": [acc.id], "selected_job_types": ["private", "govt"]})
        user = await s.get(User, student.id)
        await onboarding._finish_onboarding(msg, state, s, user, "en")
        await s.commit()

        assert user.status == "active"
        assert user.trial_ends_at is not None
        assert any("Profile complete" in a for a in msg.answers)

    # the welcome digest sent the ready job, not the held one
    assert _job_titles_sent_to(bot, student.telegram_id) == ["Ready Before Signup"]

    # the next scheduled run must not send it again
    await digest_worker.run_digest()
    assert _job_titles_sent_to(bot, student.telegram_id) == ["Ready Before Signup"]
