"""Staff (uploader) account management, owner only (Chapter 17.5)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin.deps import owner_only
from app.api.admin.schemas import StaffIn, StaffUpdate
from app.db.models import Admin
from app.db.session import get_db
from app.services.auth import hash_password

router = APIRouter(prefix="/admin/staff", tags=["admin-staff"])


@router.get("")
async def list_staff(db: AsyncSession = Depends(get_db), _admin=Depends(owner_only)) -> list[dict]:
    admins = (await db.execute(select(Admin).order_by(Admin.id))).scalars().all()
    return [
        {"id": a.id, "name": a.name, "email": a.email, "role": a.role, "is_active": a.is_active}
        for a in admins
    ]


@router.post("")
async def create_staff(
    payload: StaffIn, db: AsyncSession = Depends(get_db), _admin=Depends(owner_only)
) -> dict:
    if payload.role not in ("owner", "uploader"):
        raise HTTPException(status_code=422, detail="role must be owner or uploader")
    existing = (
        await db.execute(select(Admin).where(Admin.email == payload.email.lower()))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Email already in use")

    admin = Admin(
        name=payload.name, email=payload.email.lower(),
        password_hash=hash_password(payload.password), role=payload.role, is_active=True,
    )
    db.add(admin)
    await db.flush()
    return {"id": admin.id}


@router.put("/{staff_id}")
async def update_staff(
    staff_id: int, payload: StaffUpdate,
    db: AsyncSession = Depends(get_db), _admin=Depends(owner_only),
) -> dict:
    admin = await db.get(Admin, staff_id)
    if admin is None:
        raise HTTPException(status_code=404, detail="Staff not found")

    if payload.is_active is not None:
        admin.is_active = payload.is_active
    if payload.password:
        admin.password_hash = hash_password(payload.password)
    await db.flush()
    return {"ok": True}
