"""Twice-daily digest + locked teasers for expired users (Chapter 10.2, 18)."""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select

from app.bot.keyboards import subscribe_cta_kb
from app.bot.loader import get_bot
from app.bot.texts import t
from app.config import settings as app_config
from app.db.models import User, utcnow
from app.db.session import session_scope
from app.services.access import get_all_settings, has_access, in_trial
from app.services.alerts import send_admin_alert
from app.services.notifier import count_matching_jobs, safe_send, send_digest_to_user

logger = logging.getLogger("app.workers.digest")

_BATCH_SIZE = 500


async def digest_tick() -> None:
    """Runs every minute; triggers run_digest() at most once per configured HH:MM slot."""
    try:
        now = datetime.now(app_config.tz)
        slot = now.strftime("%H:%M")

        async with session_scope() as db:
            settings_map = await get_all_settings(db)
            digest_times = settings_map.get("digest_times", [])
            if slot not in digest_times:
                return

            slot_key = f"{now.date().isoformat()} {slot}"
            last_slot = settings_map.get("last_digest_slot")
            if last_slot == slot_key:
                return

            from app.services.access import update_settings

            await update_settings(db, {"last_digest_slot": slot_key})
            await db.commit()

        await run_digest()
    except Exception:  # noqa: BLE001
        logger.exception("digest_tick failed")
        await send_admin_alert("digest_tick_error", "See worker logs for the traceback.")


async def run_digest() -> None:
    total_users = 0
    total_sent = 0
    total_teasers = 0
    total_blocked = 0
    started = utcnow()

    last_id = 0
    while True:
        async with session_scope() as db:
            settings_map = await get_all_settings(db)
            digest_max_jobs = int(settings_map.get("digest_max_jobs", 10))
            teaser_every_hours = int(settings_map.get("teaser_every_hours", 48))
            price = int(settings_map.get("price_inr", 99))

            users = (
                await db.execute(
                    select(User)
                    .where(User.status == "active", User.id > last_id)
                    .order_by(User.id)
                    .limit(_BATCH_SIZE)
                )
            ).scalars().all()

            if not users:
                break

            bot = get_bot()
            for user in users:
                last_id = user.id
                total_users += 1
                try:
                    if has_access(user):
                        sent = await send_digest_to_user(db, bot, user, digest_max_jobs)
                        total_sent += sent
                        if user.status == "bot_blocked":
                            total_blocked += 1
                    elif user.trial_ends_at is not None:
                        # Ever had a trial (or is paid-lapsed) -> eligible for a locked teaser.
                        due = (
                            user.last_teaser_at is None
                            or (utcnow() - user.last_teaser_at).total_seconds()
                            >= teaser_every_hours * 3600
                        )
                        if due:
                            count = await count_matching_jobs(db, user, limit=100)
                            if count > 0:
                                lang = user.language or "mr"
                                result = await safe_send(
                                    bot, user.telegram_id,
                                    t(lang, "locked_teaser", count=count, price=price, days=settings_map.get("subscription_days", 30)),
                                    subscribe_cta_kb(lang, price),
                                )
                                if result == "blocked":
                                    user.status = "bot_blocked"
                                    total_blocked += 1
                                total_teasers += 1
                            user.last_teaser_at = utcnow()
                except Exception:  # noqa: BLE001
                    logger.exception("Error sending digest/teaser to user %s", user.id)

            await db.commit()

    duration = (utcnow() - started).total_seconds()
    logger.info(
        "run_digest done: users=%s jobs_sent=%s teasers=%s blocked=%s duration=%.1fs",
        total_users, total_sent, total_teasers, total_blocked, duration,
    )
