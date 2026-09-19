"""Password hashing and JWT helpers for admin authentication."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.config import settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_token(subject_id: int, role: str, *, expire_hours: int | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(hours=expire_hours if expire_hours is not None else settings.JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Raises jwt.PyJWTError (or subclasses) if invalid/expired."""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
