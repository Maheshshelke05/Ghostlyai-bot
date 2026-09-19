"""Verifies Firebase phone-auth ID tokens for the student app's login.

The app itself talks to Firebase (SMS OTP send + verify) using the Firebase client SDK; our
backend never sees the OTP. All the backend does is verify the resulting ID token's signature
server-side and trust the `phone_number` claim it carries - this is the only way to confirm a
token wasn't forged without re-implementing Google's own token verification.
"""
from __future__ import annotations

import asyncio
import json
import logging
from functools import lru_cache

from app.config import settings

logger = logging.getLogger("app.firebase_auth")


class FirebaseAuthError(Exception):
    pass


@lru_cache
def _get_app():
    import firebase_admin
    from firebase_admin import credentials

    cred = credentials.Certificate(json.loads(settings.FIREBASE_SERVICE_ACCOUNT_JSON))
    return firebase_admin.initialize_app(cred)


def _verify_sync(id_token: str) -> str:
    from firebase_admin import auth as firebase_auth_sdk

    app = _get_app()
    try:
        decoded = firebase_auth_sdk.verify_id_token(id_token, app=app)
    except Exception as exc:  # noqa: BLE001 - firebase_admin raises several distinct auth errors
        raise FirebaseAuthError("Invalid or expired login token") from exc

    phone = decoded.get("phone_number")
    if not phone:
        raise FirebaseAuthError("Token has no verified phone number")
    return phone


async def verify_phone_token(id_token: str) -> str:
    """Returns the verified E.164 phone number, or raises FirebaseAuthError."""
    if not settings.FIREBASE_SERVICE_ACCOUNT_JSON:
        logger.error("FIREBASE_SERVICE_ACCOUNT_JSON not set; cannot verify phone auth tokens")
        raise FirebaseAuthError("Phone login is not configured")
    return await asyncio.to_thread(_verify_sync, id_token)
