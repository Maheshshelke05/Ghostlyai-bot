"""Trial / paid access rules and settings helpers (Chapter 11)."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AppSetting, Subscription, User, utcnow

KNOWN_SETTINGS: dict[str, Any] = {
    "price_inr": 99,
    "subscription_days": 30,
    "trial_days": 3,
    "digest_times": ["09:00", "18:00"],
    "digest_max_jobs": 10,
    "max_categories": 3,
    "teaser_every_hours": 48,
    "last_digest_slot": None,
}


async def get_all_settings(db: AsyncSession) -> dict[str, Any]:
    rows = (await db.execute(select(AppSetting))).scalars().all()
    values = {row.key: row.value for row in rows}
    return {**KNOWN_SETTINGS, **values}


async def get_setting(db: AsyncSession, key: str, default: Any = None) -> Any:
    row = (await db.execute(select(AppSetting).where(AppSetting.key == key))).scalar_one_or_none()
    if row is not None:
        return row.value
    return KNOWN_SETTINGS.get(key, default)


async def update_settings(db: AsyncSession, updates: dict[str, Any]) -> dict[str, Any]:
    """Persist only known setting keys; unknown keys are ignored."""
    for key, value in updates.items():
        if key not in KNOWN_SETTINGS:
            continue
        row = (
            await db.execute(select(AppSetting).where(AppSetting.key == key))
        ).scalar_one_or_none()
        if row is None:
            db.add(AppSetting(key=key, value=value))
        else:
            row.value = value
    await db.flush()
    return await get_all_settings(db)


def subscription_end(user: User) -> datetime | None:
    """Latest subscription end_at for this user, or None if they never had one."""
    if not user.subscriptions:
        return None
    return max(sub.end_at for sub in user.subscriptions)


def has_paid_access(user: User, now: datetime | None = None) -> bool:
    now = now or utcnow()
    end = subscription_end(user)
    return end is not None and end > now


def in_trial(user: User, now: datetime | None = None) -> bool:
    now = now or utcnow()
    return user.trial_ends_at is not None and user.trial_ends_at > now


def has_access(user: User, now: datetime | None = None) -> bool:
    now = now or utcnow()
    return has_paid_access(user, now) or in_trial(user, now)


def access_until(user: User, now: datetime | None = None) -> datetime | None:
    """The later of paid-end / trial-end, whichever currently grants access (for display)."""
    now = now or utcnow()
    paid_end = subscription_end(user)
    if paid_end is not None and paid_end > now:
        return paid_end
    if user.trial_ends_at is not None and user.trial_ends_at > now:
        return user.trial_ends_at
    return paid_end or user.trial_ends_at


async def start_trial(db: AsyncSession, user: User, trial_days: int | None = None) -> None:
    """Starts the free trial exactly once per user."""
    if user.trial_ends_at is not None:
        return
    if trial_days is None:
        trial_days = await get_setting(db, "trial_days", 3)
    user.trial_ends_at = utcnow() + timedelta(days=trial_days)
    await db.flush()


async def extend_subscription(
    db: AsyncSession, user: User, days: int, source: str = "payment"
) -> Subscription:
    """Adds `days` after the current paid end if it's in the future, else from now."""
    now = utcnow()
    current_end = subscription_end(user)
    start = current_end if current_end and current_end > now else now
    end = start + timedelta(days=days)
    sub = Subscription(user_id=user.id, start_at=start, end_at=end, source=source)
    db.add(sub)
    user.subscriptions.append(sub)
    user.reminder_sent_for = None
    await db.flush()
    return sub


def status_line(user: User, lang: str, now: datetime | None = None) -> str:
    from app.bot.texts import t

    now = now or utcnow()
    if has_paid_access(user, now):
        end = subscription_end(user)
        return t(lang, "status_active", until=_fmt(end))
    if in_trial(user, now):
        return t(lang, "status_trial", until=_fmt(user.trial_ends_at))
    return t(lang, "status_none")


def _fmt(dt: datetime | None) -> str:
    if dt is None:
        return "-"
    from app.config import settings

    return dt.astimezone(settings.tz).strftime("%d-%m-%Y")
