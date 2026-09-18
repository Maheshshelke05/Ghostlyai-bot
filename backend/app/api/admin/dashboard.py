"""GET /admin/dashboard (Chapter 17.2)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin.deps import owner_only
from app.config import settings
from app.db.models import Job, JobDelivery, Payment, Subscription, User, utcnow
from app.db.session import get_db
from app.services import cache
from app.services.access import access_label_sql, paid_sql

router = APIRouter(prefix="/admin", tags=["admin-dashboard"])


def _ist_bounds_utc(d):
    from datetime import timezone

    start_local = datetime.combine(d, datetime.min.time(), tzinfo=settings.tz)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


@router.get("/dashboard")
async def dashboard(
    db: AsyncSession = Depends(get_db), _admin=Depends(owner_only)
) -> dict:
    # ~14 sequential aggregate queries, each a network round-trip to a remote (Neon) Postgres -
    # cheap to compute but slow to re-run on every dashboard glance, so a short cache makes
    # repeat loads (auto-refresh, pull-to-refresh, re-opening the tab) instant.
    return await cache.get_or_set("admin:dashboard", ttl_seconds=20, compute=lambda: _compute_dashboard(db))


async def _compute_dashboard(db: AsyncSession) -> dict:
    now = utcnow()
    today_ist = datetime.now(settings.tz).date()
    today_start, today_end = _ist_bounds_utc(today_ist)
    month_start_ist = today_ist.replace(day=1)
    month_start, _ = _ist_bounds_utc(month_start_ist)

    total_users = (await db.execute(select(func.count(User.id)))).scalar_one()
    active_profiles = (
        await db.execute(select(func.count(User.id)).where(User.status == "active"))
    ).scalar_one()
    onboarding = (
        await db.execute(select(func.count(User.id)).where(User.status == "onboarding"))
    ).scalar_one()
    new_today = (
        await db.execute(select(func.count(User.id)).where(User.created_at >= today_start))
    ).scalar_one()

    async def count_active(*conditions) -> int:
        stmt = select(func.count(User.id)).where(User.status == "active", *conditions)
        return (await db.execute(stmt)).scalar_one()

    # counted in the database; previously every active user was loaded into memory
    paid_count = await count_active(paid_sql(now))
    trial_count = await count_active(access_label_sql("trial", now))
    expiring_3 = await count_active(paid_sql(now), _paid_end_before(now + timedelta(days=3)))

    revenue_today = (
        await db.execute(
            select(func.coalesce(func.sum(Payment.amount_paise), 0)).where(
                Payment.status == "paid", Payment.paid_at >= today_start, Payment.paid_at < today_end
            )
        )
    ).scalar_one()
    revenue_month = (
        await db.execute(
            select(func.coalesce(func.sum(Payment.amount_paise), 0)).where(
                Payment.status == "paid", Payment.paid_at >= month_start
            )
        )
    ).scalar_one()

    jobs_today = (
        await db.execute(select(func.count(Job.id)).where(Job.created_at >= today_start))
    ).scalar_one()
    jobs_active = (
        await db.execute(select(func.count(Job.id)).where(Job.status == "active"))
    ).scalar_one()

    sent_today = (
        await db.execute(
            select(func.count(JobDelivery.id)).where(JobDelivery.sent_at >= today_start)
        )
    ).scalar_one()
    clicks_today = (
        await db.execute(
            select(func.count(JobDelivery.id)).where(
                JobDelivery.clicked_at.is_not(None), JobDelivery.clicked_at >= today_start
            )
        )
    ).scalar_one()
    ctr_today = round(clicks_today / sent_today, 4) if sent_today else 0.0

    # Two range queries for the whole week, bucketed by IST day in Python - instead of two
    # queries per day. (Grouping by an IST date in SQL isn't portable across Postgres/SQLite.)
    week_days = [today_ist - timedelta(days=i) for i in range(6, -1, -1)]
    week_start, _ = _ist_bounds_utc(week_days[0])
    revenue_by_day = {d: 0 for d in week_days}
    signups_by_day = {d: 0 for d in week_days}
    paid_rows = (
        await db.execute(
            select(Payment.paid_at, Payment.amount_paise).where(
                Payment.status == "paid", Payment.paid_at >= week_start, Payment.paid_at < today_end
            )
        )
    ).all()
    for paid_at, amount in paid_rows:
        day = _as_utc(paid_at).astimezone(settings.tz).date()
        if day in revenue_by_day:
            revenue_by_day[day] += amount or 0
    signup_rows = (
        await db.execute(
            select(User.created_at).where(User.created_at >= week_start, User.created_at < today_end)
        )
    ).scalars().all()
    for created_at in signup_rows:
        day = _as_utc(created_at).astimezone(settings.tz).date()
        if day in signups_by_day:
            signups_by_day[day] += 1
    last_7_days = [
        {"date": d.isoformat(), "revenue_inr": revenue_by_day[d] / 100, "signups": signups_by_day[d]}
        for d in week_days
    ]

    return {
        "users": {
            "total": total_users, "active_profiles": active_profiles,
            "onboarding": onboarding, "new_today": new_today,
        },
        "subscriptions": {
            "paid": paid_count, "trial": trial_count, "expiring_3_days": expiring_3,
        },
        "revenue_inr": {"today": revenue_today / 100, "month": revenue_month / 100},
        "jobs": {"today": jobs_today, "active": jobs_active},
        "deliveries": {
            "sent_today": sent_today, "clicks_today": clicks_today, "ctr_today": ctr_today,
        },
        "last_7_days": last_7_days,
    }


def _paid_end_before(cutoff):
    return (
        select(func.max(Subscription.end_at))
        .where(Subscription.user_id == User.id)
        .correlate(User)
        .scalar_subquery()
        <= cutoff
    )


def _as_utc(dt: datetime) -> datetime:
    # SQLite hands timestamps back naive; Postgres returns them aware
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
