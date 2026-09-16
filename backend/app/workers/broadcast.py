"""Sends queued broadcasts to their target audience (Chapter 13.10, 18)."""
from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select

from app.bot.loader import get_bot
from app.db.models import Broadcast, User
from app.db.session import session_scope
from app.services.access import has_access, has_paid_access, in_trial
from app.services.alerts import send_admin_alert
from app.services.notifier import safe_send

logger = logging.getLogger("app.workers.broadcast")

_MESSAGE_DELAY = 0.05


def _matches_audience(user: User, audience: str) -> bool:
    if audience == "paid":
        return has_paid_access(user)
    if audience == "trial":
        return in_trial(user) and not has_paid_access(user)
    if audience == "expired":
        return not has_access(user)
    return True  # "all"


async def audience_user_ids(db, audience: str, category_id: int | None) -> list[int]:
    users = (await db.execute(select(User).where(User.status == "active"))).scalars().all()
    ids = []
    for user in users:
        if category_id is not None and category_id not in user.category_ids:
            continue
        if _matches_audience(user, audience):
            ids.append(user.id)
    return ids


async def broadcast_runner() -> None:
    """Picks the next queued broadcast (if any) and sends it. Scheduled every 30 seconds."""
    try:
        broadcast_id: int | None = None
        async with session_scope() as db:
            broadcast = (
                await db.execute(
                    select(Broadcast)
                    .where(Broadcast.status == "queued")
                    .order_by(Broadcast.created_at)
                    .with_for_update(skip_locked=True)
                    .limit(1)
                )
            ).scalar_one_or_none()
            if broadcast is not None:
                broadcast.status = "running"
                await db.flush()
                broadcast_id = broadcast.id
            await db.commit()

        if broadcast_id is not None:
            await _run_broadcast(broadcast_id)
    except Exception:  # noqa: BLE001
        logger.exception("broadcast_runner failed")
        await send_admin_alert("broadcast_error", "See worker logs for the traceback.")


async def _run_broadcast(broadcast_id: int) -> None:
    async with session_scope() as db:
        broadcast = await db.get(Broadcast, broadcast_id)
        if broadcast is None:
            return
        text = broadcast.text
        user_ids = await audience_user_ids(db, broadcast.audience, broadcast.category_id)
        broadcast.total = len(user_ids)
        await db.commit()

    bot = get_bot()
    sent = 0
    failed = 0

    for user_id in user_ids:
        async with session_scope() as db:
            user = await db.get(User, user_id)
            if user is None:
                failed += 1
                continue
            result = await safe_send(bot, user.telegram_id, text)
            if result == "ok":
                sent += 1
            else:
                failed += 1
                if result == "blocked":
                    user.status = "bot_blocked"
            await db.commit()
        await asyncio.sleep(_MESSAGE_DELAY)

    async with session_scope() as db:
        broadcast = await db.get(Broadcast, broadcast_id)
        if broadcast is not None:
            broadcast.sent = sent
            broadcast.failed = failed
            broadcast.status = "done"
            await db.commit()

    logger.info("broadcast %s done: total=%s sent=%s failed=%s", broadcast_id, len(user_ids), sent, failed)
