"""Support inbox: student help messages and admin replies."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
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
from app.services.push import send_push_to_student
from app.services.storage import get_support_image_url

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
    # Pull last_in/last_out along with each user row (add_columns keeps stmt's existing filters)
    # so "awaiting reply" is answered by the same query, and batch-fetch every page's latest
    # message in one extra round-trip - this used to run 2 extra queries per user (up to 200
    # round-trips for a full page), which is exactly what made this screen take several
    # seconds to load.
    paged_stmt = (
        stmt.add_columns(last_in.label("last_in"), last_out.label("last_out"))
        .order_by(last_in.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    rows = (await db.execute(paged_stmt)).all()

    user_ids = [user.id for user, _, _ in rows]
    latest_by_user: dict[int, SupportMessage] = {}
    if user_ids:
        all_recent = (
            await db.execute(
                select(SupportMessage)
                .where(SupportMessage.user_id.in_(user_ids))
                .order_by(SupportMessage.user_id, SupportMessage.created_at.desc())
            )
        ).scalars().all()
        for m in all_recent:
            latest_by_user.setdefault(m.user_id, m)  # first hit per user_id is the latest

    items = []
    for user, last_in_at, last_out_at in rows:
        last = latest_by_user.get(user.id)
        awaiting_reply = last_in_at is not None and (last_out_at is None or last_out_at < last_in_at)
        items.append({
            "user_id": user.id,
            "full_name": user.full_name,
            "username": user.username,
            "phone": user.phone,
            "status": user.status,
            "last_message": last.text if last else None,
            "last_direction": last.direction if last else None,
            "last_at": last.created_at.isoformat() if last else None,
            "awaiting_reply": bool(awaiting_reply),
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
                "id": m.id, "direction": m.direction, "subject": m.subject, "text": m.text,
                "image_url": f"/admin/support/image/{m.id}" if m.image_path else None,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    }


@router.get("/image/{message_id}")
async def get_message_image(
    message_id: int, db: AsyncSession = Depends(get_db), _admin=Depends(owner_only)
):
    message = await db.get(SupportMessage, message_id)
    if message is None or not message.image_path:
        raise HTTPException(status_code=404, detail="Image not found")

    signed_url = await get_support_image_url(message.image_path)
    if signed_url is not None:
        return RedirectResponse(signed_url)

    path = Path(message.image_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Image file not found")
    return FileResponse(path)


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

    # Push notification is separate from (and never a substitute for) the Telegram send above -
    # an app-only student (telegram_id=None) has "skipped" for `result`, and a dual student
    # gets both channels.
    preview = payload.text if len(payload.text) <= 120 else payload.text[:117] + "..."
    await send_push_to_student(user, "Support replied", preview, {"type": "support"})

    # stored either way, so the thread still shows what the admin tried to send
    db.add(SupportMessage(user_id=user_id, admin_id=admin.id, direction="out", text=payload.text))
    await db.flush()
    return {"result": result}
