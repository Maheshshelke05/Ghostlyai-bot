"""POST /student/support, GET /student/support - the student app's support thread.

Same support_messages table and admin-reply flow as the bot's /support command
(app/bot/handlers/support.py, app/api/admin/support.py) - a student can freely mix channels
(ask via Telegram, read the reply in the app, or vice versa) since both write to one thread.
A message can optionally carry a subject and one screenshot/photo attachment.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.student.deps import current_student
from app.api.student.schemas import SupportMessageOut, SupportThreadOut
from app.db.models import SupportMessage, User
from app.db.session import get_db
from app.services.push import send_push_to_admins
from app.services.storage import get_support_image_url, is_supported_image_mime, save_support_image

router = APIRouter(prefix="/student/support", tags=["student-support"])

MAX_SUPPORT_TEXT = 1000
MAX_SUPPORT_SUBJECT = 120
MAX_IMAGE_MB = 5


async def _to_out(m: SupportMessage) -> SupportMessageOut:
    image_url = None
    if m.image_path:
        image_url = await get_support_image_url(m.image_path) or f"/student/support/{m.id}/image"
    return SupportMessageOut(
        id=m.id, direction=m.direction, subject=m.subject, text=m.text,
        image_url=image_url, created_at=m.created_at.isoformat(),
    )


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
    return SupportThreadOut(messages=[await _to_out(m) for m in messages])


@router.post("", response_model=SupportMessageOut)
async def send_message(
    text: str = Form(..., min_length=5, max_length=MAX_SUPPORT_TEXT),
    subject: Optional[str] = Form(default=None, max_length=MAX_SUPPORT_SUBJECT),
    image: Optional[UploadFile] = File(default=None),
    user: User = Depends(current_student),
    db: AsyncSession = Depends(get_db),
) -> SupportMessageOut:
    text = text.strip()[:MAX_SUPPORT_TEXT]
    subject_clean = subject.strip()[:MAX_SUPPORT_SUBJECT] if subject and subject.strip() else None

    message = SupportMessage(user_id=user.id, direction="in", text=text, subject=subject_clean)
    db.add(message)
    await db.flush()

    if image is not None:
        data = await image.read()
        mime = image.content_type or ""
        if not is_supported_image_mime(mime):
            raise HTTPException(status_code=400, detail="Only JPEG, PNG or WEBP images are supported")
        if len(data) > MAX_IMAGE_MB * 1024 * 1024:
            raise HTTPException(status_code=400, detail=f"Image must be under {MAX_IMAGE_MB}MB")
        message.image_path = await save_support_image(message.id, data, mime)
        await db.flush()

    preview = text if len(text) <= 120 else text[:117] + "..."
    title = f"New support message (app) — {user.full_name or 'a student'}"
    if subject_clean:
        title = f"{title}: {subject_clean}"
    await send_push_to_admins(db, title, preview, {"type": "support"})

    return await _to_out(message)


@router.get("/{message_id}/image")
async def get_message_image(
    message_id: int, user: User = Depends(current_student), db: AsyncSession = Depends(get_db)
):
    message = await db.get(SupportMessage, message_id)
    if message is None or message.user_id != user.id or not message.image_path:
        raise HTTPException(status_code=404, detail="Image not found")

    signed_url = await get_support_image_url(message.image_path)
    if signed_url is not None:
        return RedirectResponse(signed_url)

    path = Path(message.image_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Image file not found")
    return FileResponse(path)
