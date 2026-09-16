"""Regression test: if a user blocks the bot mid-digest, jobs in chunks that were never
actually delivered must not be left marked as "delivered" (Chapter 10.2)."""
from sqlalchemy import select

from app.db.models import JobDelivery
from app.services.notifier import send_digest_to_user

from tests.conftest import FakeBot, make_job, make_user


async def test_full_digest_sent_when_not_blocked(db, categories, fake_bot: FakeBot):
    user = await make_user(db, category_slugs=["accounts-finance"])
    for i in range(7):
        await make_job(db, categories, title=f"Job {i}", apply_link=f"https://example.com/{i}")

    sent = await send_digest_to_user(db, fake_bot, user, limit=10)

    assert sent == 7
    assert len(fake_bot.sent) == 2  # 5 + 2, chunked by 5 per message
    deliveries = (await db.execute(select(JobDelivery).where(JobDelivery.user_id == user.id))).scalars().all()
    assert len(deliveries) == 7


async def test_blocked_mid_digest_only_keeps_delivered_chunk(db, categories, fake_bot: FakeBot):
    user = await make_user(db, category_slugs=["accounts-finance"])
    for i in range(7):
        await make_job(db, categories, title=f"Job {i}", apply_link=f"https://example.com/{i}")

    # Allow the first chunk (5 jobs -> 1 message) through, then simulate the user blocking the bot.
    fake_bot.block_after[user.telegram_id] = 1

    sent = await send_digest_to_user(db, fake_bot, user, limit=10)

    assert sent == 5
    assert len(fake_bot.sent) == 1
    assert user.status == "bot_blocked"

    # Only the 5 jobs from the successfully sent chunk should be recorded as delivered -
    # the 2 jobs in the never-sent second chunk must NOT be stuck as "already delivered",
    # otherwise this user would never be offered them again even after unblocking.
    deliveries = (await db.execute(select(JobDelivery).where(JobDelivery.user_id == user.id))).scalars().all()
    assert len(deliveries) == 5
