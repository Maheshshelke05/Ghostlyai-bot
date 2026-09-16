"""GET / PUT /admin/settings (Chapter 17.5)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin.deps import owner_only
from app.api.admin.schemas import SettingsIn
from app.db.session import get_db
from app.services.access import get_all_settings, update_settings

router = APIRouter(prefix="/admin/settings", tags=["admin-settings"])


@router.get("")
async def read_settings(db: AsyncSession = Depends(get_db), _admin=Depends(owner_only)) -> dict:
    return await get_all_settings(db)


@router.put("")
async def write_settings(
    payload: SettingsIn, db: AsyncSession = Depends(get_db), _admin=Depends(owner_only)
) -> dict:
    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    return await update_settings(db, updates)
