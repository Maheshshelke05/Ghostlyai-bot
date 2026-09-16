"""T5-T9: trial/paid access rules and subscription extend/stacking (Chapter 21.1)."""
from datetime import timedelta

from app.db.models import utcnow
from app.services.access import extend_subscription, has_access, start_trial

from tests.conftest import make_user


async def test_has_access_true_when_trial_ends_tomorrow(db):
    user = await make_user(db, trial_ends_at=utcnow() + timedelta(days=1))
    assert has_access(user) is True


async def test_has_access_false_when_trial_and_subscription_expired(db):
    user = await make_user(db, trial_ends_at=utcnow() - timedelta(days=1))
    assert has_access(user) is False


async def test_extend_subscription_adds_after_current_future_end(db):
    user = await make_user(db, paid_until=utcnow() + timedelta(days=10))
    await extend_subscription(db, user, 30)
    await db.refresh(user, attribute_names=["subscriptions"])
    end = max(s.end_at for s in user.subscriptions)
    expected = utcnow() + timedelta(days=40)
    assert abs((end - expected).total_seconds()) < 5


async def test_extend_subscription_from_now_when_expired(db):
    user = await make_user(db, paid_until=utcnow() - timedelta(days=5))
    await extend_subscription(db, user, 30)
    await db.refresh(user, attribute_names=["subscriptions"])
    end = max(s.end_at for s in user.subscriptions)
    expected = utcnow() + timedelta(days=30)
    assert abs((end - expected).total_seconds()) < 5


async def test_start_trial_is_idempotent(db):
    user = await make_user(db, trial_ends_at=None)
    await start_trial(db, user, trial_days=3)
    first_end = user.trial_ends_at
    await start_trial(db, user, trial_days=3)
    assert user.trial_ends_at == first_end
