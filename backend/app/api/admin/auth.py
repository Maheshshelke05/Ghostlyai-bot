"""POST /admin/auth/login, GET /admin/auth/me, POST /admin/auth/change-password."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin.deps import current_admin
from app.api.admin.schemas import AdminOut, ChangePasswordIn, LoginIn, TokenOut
from app.db.models import Admin
from app.db.session import get_db
from app.services import ratelimit
from app.services.auth import create_token, hash_password, verify_password

router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])


def _client_ip(request: Request) -> str:
    # Render (and any proxy) puts the real client in X-Forwarded-For; first hop is the client.
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/login", response_model=TokenOut)
async def login(payload: LoginIn, request: Request, db: AsyncSession = Depends(get_db)) -> TokenOut:
    email = payload.email.lower()
    limit_key = f"{_client_ip(request)}|{email}"
    wait = ratelimit.seconds_until_allowed(limit_key)
    if wait:
        raise HTTPException(
            status_code=429,
            detail="Too many failed login attempts. Try again in a few minutes.",
            headers={"Retry-After": str(wait)},
        )

    admin = (await db.execute(select(Admin).where(Admin.email == email))).scalar_one_or_none()
    if admin is None or not admin.is_active or not verify_password(payload.password, admin.password_hash):
        ratelimit.record_failure(limit_key)
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    ratelimit.clear(limit_key)
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
