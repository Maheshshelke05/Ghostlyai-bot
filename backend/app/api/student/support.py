"""POST /student/support, GET /student/support - the student app's support thread.

Same support_messages table and admin-reply flow as the bot's /support command
(app/bot/handlers/support.py, app/api/admin/support.py) - a student can freely mix channels
(ask via Telegram, read the reply in the app, or vice versa) since both write to one thread.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.student.deps import current_student
from app.api.student.schemas import SupportMessageIn, SupportMessageOut, SupportThreadOut
from app.db.models import SupportMessage, User
from app.db.session import get_db
from app.services.push import send_push_to_admins

router = APIRouter(prefix="/student/support", tags=["student-support"])

MAX_SUPPORT_TEXT = 1000


@router.get("", response_model=SupportThreadOut)
async def get_thread(
    user: User = Depends(current_student), db: AsyncSession = Depends(get_db)
) -> SupportThreadOut:
    messages = (
        await db.execute(
            select(SupportMessage)
            .where(SupportMessage.user_id == user.id)
            .order_by(SupportMessage.created_at)
        )
    ).scalars().all()
    return SupportThreadOut(
        messages=[
            SupportMessageOut(
                id=m.id, direction=m.direction, text=m.text, created_at=m.created_at.isoformat()
            )
            for m in messages
        ]
    )


@router.post("", response_model=SupportMessageOut)
async def send_message(
    payload: SupportMessageIn,
    user: User = Depends(current_student),
    db: AsyncSession = Depends(get_db),
) -> SupportMessageOut:
    text = payload.text.strip()[:MAX_SUPPORT_TEXT]
    message = SupportMessage(user_id=user.id, direction="in", text=text)
    db.add(message)
    await db.flush()

    preview = text if len(text) <= 120 else text[:117] + "..."
    await send_push_to_admins(
        db, f"New support message (app) — {user.full_name or 'a student'}", preview, {"type": "support"}
    )

    return SupportMessageOut(
        id=message.id, direction=message.direction, text=message.text,
        created_at=message.created_at.isoformat(),
    )
