"""Student app authentication dependency: current_student. Mirrors app/api/admin/deps.py."""
from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.session import get_db
from app.services.auth import decode_token

STUDENT_ROLE = "student"

_bearer = HTTPBearer(auto_error=False)


async def current_student(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_token(credentials.credentials)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if payload.get("role") != STUDENT_ROLE:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    user = await db.get(User, int(user_id)) if user_id else None
    if user is None or user.status == "blocked":
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user
