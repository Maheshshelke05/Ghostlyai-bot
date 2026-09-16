"""Telegram webhook endpoint: verifies the secret token and feeds updates to aiogram."""
from __future__ import annotations

import asyncio
import logging

from aiogram.types import Update
from fastapi import APIRouter, Header, HTTPException, Request, Response

from app.bot.loader import get_bot, get_dispatcher
from app.config import settings

logger = logging.getLogger("app.webhooks.telegram")
router = APIRouter(tags=["webhooks"])

_background_tasks: set[asyncio.Task] = set()


@router.post("/webhooks/telegram")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> Response:
    if settings.TELEGRAM_WEBHOOK_SECRET:
        if x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
            raise HTTPException(status_code=403, detail="Invalid secret token")

    body = await request.json()
    try:
        update = Update.model_validate(body)
    except Exception:  # noqa: BLE001
        logger.exception("Invalid Telegram update payload")
        return Response(status_code=200)

    task = asyncio.create_task(_process_update(update))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return Response(status_code=200)


async def _process_update(update: Update) -> None:
    try:
        dp = get_dispatcher()
        await dp.feed_update(get_bot(), update)
    except Exception:  # noqa: BLE001
        logger.exception("Error processing Telegram update %s", update.update_id)
