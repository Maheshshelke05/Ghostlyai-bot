"""GET /admin/dashboard (Chapter 17.2)."""
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin.deps import owner_only
from app.config import settings
from app.db.models import Job, JobDelivery, Payment, User, utcnow
from app.db.session import get_db
from app.services.access import has_access

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

    active_users = (
        await db.execute(select(User).where(User.status == "active"))
    ).scalars().all()
    paid_count = sum(1 for u in active_users if has_access(u) and _has_paid(u, now))
    trial_count = sum(1 for u in active_users if has_access(u) and not _has_paid(u, now))
    expiring_3 = 0
    for u in active_users:
        end = _paid_end(u)
        if end and now < end <= now + timedelta(days=3):
            expiring_3 += 1

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

    last_7_days = []
    for i in range(6, -1, -1):
        d = today_ist - timedelta(days=i)
        d_start, d_end = _ist_bounds_utc(d)
        rev = (
            await db.execute(
                select(func.coalesce(func.sum(Payment.amount_paise), 0)).where(
                    Payment.status == "paid", Payment.paid_at >= d_start, Payment.paid_at < d_end
                )
            )
        ).scalar_one()
        signups = (
            await db.execute(
                select(func.count(User.id)).where(User.created_at >= d_start, User.created_at < d_end)
            )
        ).scalar_one()
        last_7_days.append({"date": d.isoformat(), "revenue_inr": rev / 100, "signups": signups})

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


def _paid_end(user: User):
    if not user.subscriptions:
        return None
    return max(sub.end_at for sub in user.subscriptions)


def _has_paid(user: User, now) -> bool:
    end = _paid_end(user)
    return end is not None and end > now
