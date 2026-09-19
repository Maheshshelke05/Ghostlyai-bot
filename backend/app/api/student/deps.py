"""Student app authentication dependencies: current_student, current_pending_student.
Mirrors app/api/admin/deps.py."""
from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.session import get_db
from app.services.auth import decode_token

STUDENT_ROLE = "student"
# A signup_token's role - deliberately distinct from STUDENT_ROLE so it can only ever be used
# to call POST /student/auth/set-password, never any other student endpoint, even though both
# are plain JWTs signed with the same secret.
STUDENT_PENDING_ROLE = "student_pending"

_bearer = HTTPBearer(auto_error=False)


async def _decode_for_role(
    credentials: HTTPAuthorizationCredentials | None, db: AsyncSession, role: str
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_token(credentials.credentials)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if payload.get("role") != role:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    user = await db.get(User, int(user_id)) if user_id else None
    if user is None or user.status == "blocked":
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


async def current_student(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await _decode_for_role(credentials, db, STUDENT_ROLE)


async def current_pending_student(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await _decode_for_role(credentials, db, STUDENT_PENDING_ROLE)
