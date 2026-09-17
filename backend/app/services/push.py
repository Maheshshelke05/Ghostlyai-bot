"""Push notifications to the admin app via Expo's push service.

This is separate from `services/alerts.py`, which sends error alerts to a Telegram chat -
this one sends real OS-level push notifications to whichever admins have opened the app and
registered a device (PUT /admin/auth/push-token), so a new signup or support message reaches
them even while the app is fully closed.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Admin

logger = logging.getLogger("app.push")

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
# Expo caps a single request at 100 messages; our admin team is tiny, but batch anyway.
_BATCH_SIZE = 100


async def get_admin_push_tokens(db: AsyncSession, *, exclude_admin_id: int | None = None) -> list[str]:
    stmt = select(Admin.expo_push_token).where(
        Admin.expo_push_token.is_not(None), Admin.is_active.is_(True)
    )
    if exclude_admin_id is not None:
        stmt = stmt.where(Admin.id != exclude_admin_id)
    rows = (await db.execute(stmt)).scalars().all()
    return [t for t in rows if t]


async def send_push_to_admins(
    db: AsyncSession,
    title: str,
    body: str,
    data: dict[str, Any] | None = None,
    *,
    exclude_admin_id: int | None = None,
) -> None:
    """Best-effort: logs and swallows any failure so a push outage never breaks the bot/worker
    flow that triggered it (onboarding, a support message, the digest, ...)."""
    tokens = await get_admin_push_tokens(db, exclude_admin_id=exclude_admin_id)
    if not tokens:
        return

    messages = [
        {"to": token, "title": title, "body": body, "data": data or {}, "sound": "default", "priority": "high"}
        for token in tokens
    ]
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            for i in range(0, len(messages), _BATCH_SIZE):
                resp = await client.post(
                    EXPO_PUSH_URL,
                    json=messages[i : i + _BATCH_SIZE],
                    headers={"Content-Type": "application/json", "Accept": "application/json"},
                )
                if resp.status_code >= 400:
                    logger.warning("Expo push send failed (%s): %s", resp.status_code, resp.text[:300])
    except Exception:  # noqa: BLE001
        logger.exception("Failed to send Expo push notifications")
