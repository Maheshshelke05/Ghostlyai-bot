"""User list/detail, extend/message/block/unblock, resume download, delete (Chapter 17.4)."""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin.deps import owner_only
from app.api.admin.schemas import ExtendIn, MessageIn
from app.bot.loader import get_bot
from app.bot.texts import t
from app.db.models import JobDelivery, Payment, User, utcnow
from app.db.session import get_db
from app.services.access import (
    access_label_sql,
    access_until,
    access_until_between_sql,
    extend_subscription,
    format_date_ist,
    has_paid_access,
    in_trial,
    reactivate_if_bot_blocked,
)
from app.services.notifier import safe_send
from app.services.storage import delete_resume, get_resume_url

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


def _access_label(user: User, now) -> str:
    if has_paid_access(user, now):
        return "paid"
    if in_trial(user, now):
        return "trial"
    return "none"


def _user_row(user: User) -> dict:
    now = utcnow()
    until = access_until(user, now)
    return {
        "id": user.id, "telegram_id": user.telegram_id, "username": user.username,
        "full_name": user.full_name, "phone": user.phone, "district": user.district,
        "language": user.language, "status": user.status,
        "access": _access_label(user, now),
        "access_until": until.isoformat() if until else None,
        "categories": [link.category.slug for link in user.category_links],
        "created_at": user.created_at.isoformat(),
    }


@router.get("")
async def list_users(
    q: Optional[str] = None,
    status: Optional[str] = None,
    access: Optional[str] = None,
    expiring: Optional[int] = None,
    district: Optional[str] = None,
    page: int = 1,
    size: int = 30,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(owner_only),
) -> dict:
    stmt = select(User)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            (User.full_name.ilike(like)) | (User.phone.ilike(like)) | (User.username.ilike(like))
        )
    if status:
        stmt = stmt.where(User.status == status)
    if district:
        stmt = stmt.where(User.district == district)

    # filter, count and paginate in the database - never pull every user into memory
    now = utcnow()
    if access:
        stmt = stmt.where(access_label_sql(access, now))
    if expiring:
        stmt = stmt.where(access_until_between_sql(now, now + timedelta(days=expiring)))

    page = max(page, 1)
    size = max(1, min(size, 100))
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    page_users = (
        await db.execute(stmt.order_by(User.created_at.desc()).offset((page - 1) * size).limit(size))
    ).scalars().all()
    return {"items": [_user_row(u) for u in page_users], "total": total, "page": page, "size": size}


@router.get("/{user_id}")
async def get_user(user_id: int, db: AsyncSession = Depends(get_db), _admin=Depends(owner_only)) -> dict:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    payments = (
        await db.execute(select(Payment).where(Payment.user_id == user_id).order_by(Payment.created_at.desc()))
    ).scalars().all()

    deliveries = (
        await db.execute(
            select(JobDelivery).where(JobDelivery.user_id == user_id)
            .order_by(JobDelivery.sent_at.desc()).limit(20)
        )
    ).scalars().all()

    sent_total = (
        await db.execute(select(func.count(JobDelivery.id)).where(JobDelivery.user_id == user_id))
    ).scalar_one()
    clicks_total = (
        await db.execute(
            select(func.count(JobDelivery.id)).where(
                JobDelivery.user_id == user_id, JobDelivery.clicked_at.is_not(None)
            )
        )
    ).scalar_one()

    return {
        "user": _user_row(user),
        "profile": (
            {
                "education": user.profile.education, "course": user.profile.course,
                "skills": user.profile.skills, "experience_years": float(user.profile.experience_years),
                "summary": user.profile.summary, "has_resume": bool(user.profile.resume_path),
            }
            if user.profile else None
        ),
        "categories": [link.category.slug for link in user.category_links],
        "subscriptions": [
            {"start_at": s.start_at.isoformat(), "end_at": s.end_at.isoformat(), "source": s.source}
            for s in user.subscriptions
        ],
        "payments": [
            {
                "id": p.id, "amount_paise": p.amount_paise, "status": p.status,
                "paid_at": p.paid_at.isoformat() if p.paid_at else None,
                "razorpay_payment_id": p.razorpay_payment_id,
            }
            for p in payments
        ],
        "recent_deliveries": [
            {
                "job_id": d.job_id, "title": d.job.title if d.job else None,
                "sent_at": d.sent_at.isoformat(), "clicked": d.clicked_at is not None,
            }
            for d in deliveries
        ],
        "stats": {"sent": sent_total, "clicks": clicks_total},
    }


@router.post("/{user_id}/extend")
async def extend_user(
    user_id: int, payload: ExtendIn, db: AsyncSession = Depends(get_db), _admin=Depends(owner_only)
) -> dict:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    sub = await extend_subscription(db, user, payload.days, source="admin")
    reactivate_if_bot_blocked(user)

    if payload.notify:
        lang = user.language or "mr"
        result = await safe_send(
            get_bot(), user.telegram_id, t(lang, "payment_success", until=format_date_ist(sub.end_at))
        )
        if result == "blocked":
            user.status = "bot_blocked"
    await db.flush()

    return {"access_until": sub.end_at.isoformat()}


@router.post("/{user_id}/message")
async def message_user(
    user_id: int, payload: MessageIn, db: AsyncSession = Depends(get_db), _admin=Depends(owner_only)
) -> dict:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    result = await safe_send(get_bot(), user.telegram_id, payload.text)
    if result == "blocked":
        user.status = "bot_blocked"
        await db.flush()
    return {"result": result}


@router.post("/{user_id}/block")
async def block_user(user_id: int, db: AsyncSession = Depends(get_db), _admin=Depends(owner_only)) -> dict:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.status = "blocked"
    await db.flush()
    return {"status": user.status}


@router.post("/{user_id}/unblock")
async def unblock_user(user_id: int, db: AsyncSession = Depends(get_db), _admin=Depends(owner_only)) -> dict:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.status = "active" if user.category_links else "onboarding"
    await db.flush()
    return {"status": user.status}


@router.get("/{user_id}/resume")
async def download_resume(user_id: int, db: AsyncSession = Depends(get_db), _admin=Depends(owner_only)):
    user = await db.get(User, user_id)
    if user is None or user.profile is None or not user.profile.resume_path:
        raise HTTPException(status_code=404, detail="Resume not found")

    resume_path = user.profile.resume_path
    signed_url = await get_resume_url(resume_path)
    if signed_url is not None:
        return RedirectResponse(signed_url)

    path = Path(resume_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Resume file not found")
    filename = f"resume_{user_id}{path.suffix}"
    return FileResponse(path, filename=filename)


@router.delete("/{user_id}")
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db), _admin=Depends(owner_only)) -> dict:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    await db.execute(
        Payment.__table__.update().where(Payment.user_id == user_id).values(user_id=None)
    )
    await delete_resume(user_id, user.profile.resume_path if user.profile else None)
    await db.delete(user)
    await db.flush()
    return {"ok": True}
