"""Sends short error alerts to the owner's Telegram chat, de-duplicated per hour (Chapter 18)."""
from __future__ import annotations

import logging
import time

from app.config import settings

logger = logging.getLogger("app.alerts")

_DEDUPE_SECONDS = 3600
_last_sent: dict[str, float] = {}


async def send_admin_alert(error_type: str, message: str) -> None:
    if not settings.ADMIN_ALERT_CHAT_ID:
        return

    now = time.monotonic()
    last = _last_sent.get(error_type)
    if last is not None and (now - last) < _DEDUPE_SECONDS:
        return
    _last_sent[error_type] = now

    try:
        from app.bot.loader import get_bot

        await get_bot().send_message(
            int(settings.ADMIN_ALERT_CHAT_ID), f"⚠️ {error_type}\n{message}"[:4000]
        )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to send admin alert (error_type=%s)", error_type)
