"""POST /admin/auth/login, GET /admin/auth/me, POST /admin/auth/change-password."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin.deps import current_admin
from app.api.admin.schemas import AdminOut, ChangePasswordIn, LoginIn, TokenOut
from app.db.models import Admin
from app.db.session import get_db
from app.services.auth import create_token, hash_password, verify_password

router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])


@router.post("/login", response_model=TokenOut)
async def login(payload: LoginIn, db: AsyncSession = Depends(get_db)) -> TokenOut:
    admin = (
        await db.execute(select(Admin).where(Admin.email == payload.email.lower()))
    ).scalar_one_or_none()
    if admin is None or not admin.is_active or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="Email kiva password chukicha")

    token = create_token(admin.id, admin.role)
    return TokenOut(access_token=token, admin=AdminOut.model_validate(admin, from_attributes=True))


@router.get("/me", response_model=AdminOut)
async def me(admin: Admin = Depends(current_admin)) -> AdminOut:
    return AdminOut.model_validate(admin, from_attributes=True)


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordIn,
    admin: Admin = Depends(current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not verify_password(payload.old_password, admin.password_hash):
        raise HTTPException(status_code=400, detail="Old password is incorrect")
    admin.password_hash = hash_password(payload.new_password)
    await db.flush()
    return {"ok": True}
