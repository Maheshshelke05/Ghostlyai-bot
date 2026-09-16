"""Admin authentication dependencies: current_admin (any role), owner_only."""
from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Admin
from app.db.session import get_db
from app.services.auth import decode_token

_bearer = HTTPBearer(auto_error=False)


async def current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> Admin:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_token(credentials.credentials)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    admin_id = payload.get("sub")
    admin = await db.get(Admin, int(admin_id)) if admin_id else None
    if admin is None or not admin.is_active:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return admin


async def owner_only(admin: Admin = Depends(current_admin)) -> Admin:
    if admin.role != "owner":
        raise HTTPException(status_code=403, detail="Owner role required")
    return admin
