"""Broadcast preview/create/status (Chapter 13.10, 17.5). The worker actually sends messages."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin.deps import owner_only
from app.api.admin.schemas import BroadcastIn, BroadcastPreviewIn
from app.db.models import Admin, Broadcast
from app.db.session import get_db
from app.workers.broadcast import audience_user_ids

router = APIRouter(prefix="/admin/broadcast", tags=["admin-broadcast"])

VALID_AUDIENCES = {"all", "paid", "trial", "expired"}


@router.post("/preview-count")
async def preview_count(
    payload: BroadcastPreviewIn, db: AsyncSession = Depends(get_db), _admin=Depends(owner_only)
) -> dict:
    if payload.audience not in VALID_AUDIENCES:
        raise HTTPException(status_code=422, detail=f"audience must be one of {VALID_AUDIENCES}")
    ids = await audience_user_ids(db, payload.audience, payload.category_id)
    return {"count": len(ids)}


@router.post("")
async def create_broadcast(
    payload: BroadcastIn, db: AsyncSession = Depends(get_db), admin: Admin = Depends(owner_only)
) -> dict:
    if payload.audience not in VALID_AUDIENCES:
        raise HTTPException(status_code=422, detail=f"audience must be one of {VALID_AUDIENCES}")

    broadcast = Broadcast(
        admin_id=admin.id, text=payload.text, audience=payload.audience,
        category_id=payload.category_id, status="queued",
    )
    db.add(broadcast)
    await db.flush()
    return {"id": broadcast.id, "total": broadcast.total}


@router.get("/{broadcast_id}")
async def get_broadcast(
    broadcast_id: int, db: AsyncSession = Depends(get_db), _admin=Depends(owner_only)
) -> dict:
    broadcast = await db.get(Broadcast, broadcast_id)
    if broadcast is None:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    return {
        "id": broadcast.id, "status": broadcast.status,
        "total": broadcast.total, "sent": broadcast.sent, "failed": broadcast.failed,
    }
