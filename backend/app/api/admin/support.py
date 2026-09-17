"""Support inbox: student help messages and admin replies."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin.deps import owner_only
from app.api.admin.schemas import MessageIn
from app.bot.loader import get_bot
from app.bot.texts import t
from app.db.models import Admin, SupportMessage, User
from app.db.session import get_db
from app.services.access import reactivate_if_bot_blocked
from app.services.notifier import safe_send

router = APIRouter(prefix="/admin/support", tags=["admin-support"])


def _last_at(direction: str):
    return (
        select(func.max(SupportMessage.created_at))
        .where(SupportMessage.user_id == User.id, SupportMessage.direction == direction)
        .correlate(User)
        .scalar_subquery()
    )


def _awaiting_reply_clause():
    """Users whose newest inbound message is newer than any reply we've sent."""
    last_in, last_out = _last_at("in"), _last_at("out")
    return and_(last_in.is_not(None), (last_out.is_(None)) | (last_out < last_in))


@router.get("")
async def list_threads(
    status: Optional[str] = None,  # "open" (awaiting reply) | anything else = all threads
    q: Optional[str] = None,
    page: int = 1,
    size: int = 30,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(owner_only),
) -> dict:
    last_in, last_out = _last_at("in"), _last_at("out")
    stmt = select(User).where(last_in.is_not(None))
    if status == "open":
        stmt = stmt.where(_awaiting_reply_clause())
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            (User.full_name.ilike(like)) | (User.phone.ilike(like)) | (User.username.ilike(like))
        )

    page = max(page, 1)
    size = max(1, min(size, 100))
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    users = (
        await db.execute(stmt.order_by(last_in.desc()).offset((page - 1) * size).limit(size))
    ).scalars().all()

    items = []
    for user in users:
        last = (
            await db.execute(
                select(SupportMessage)
                .where(SupportMessage.user_id == user.id)
                .order_by(SupportMessage.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        unanswered = (
            await db.execute(select(func.count()).select_from(
                select(User.id).where(User.id == user.id, _awaiting_reply_clause()).subquery()
            ))
        ).scalar_one()
        items.append({
            "user_id": user.id,
            "full_name": user.full_name,
            "username": user.username,
            "phone": user.phone,
            "status": user.status,
            "last_message": last.text if last else None,
            "last_direction": last.direction if last else None,
            "last_at": last.created_at.isoformat() if last else None,
            "awaiting_reply": bool(unanswered),
        })
    return {"items": items, "total": total, "page": page, "size": size}


@router.get("/{user_id}")
async def get_thread(
    user_id: int, db: AsyncSession = Depends(get_db), _admin=Depends(owner_only)
) -> dict:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    messages = (
        await db.execute(
            select(SupportMessage)
            .where(SupportMessage.user_id == user_id)
            .order_by(SupportMessage.created_at)
        )
    ).scalars().all()

    return {
        "user": {
            "id": user.id, "full_name": user.full_name, "username": user.username,
            "phone": user.phone, "status": user.status, "language": user.language,
        },
        "messages": [
            {
                "id": m.id, "direction": m.direction, "text": m.text,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    }


@router.post("/{user_id}/reply")
async def reply(
    user_id: int,
    payload: MessageIn,
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(owner_only),
) -> dict:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    lang = user.language or "mr"
    result = await safe_send(get_bot(), user.telegram_id, t(lang, "support_reply", text=payload.text))
    if result == "blocked":
        user.status = "bot_blocked"
    elif result == "ok":
        reactivate_if_bot_blocked(user)

    # stored either way, so the thread still shows what the admin tried to send
    db.add(SupportMessage(user_id=user_id, admin_id=admin.id, direction="out", text=payload.text))
    await db.flush()
    return {"result": result}
