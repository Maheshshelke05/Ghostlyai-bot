"""Expiry reminders: 3 days / 1 day before paid subscription ends, and trial's last day (Chapter 11.4)."""
from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy import select

from app.bot.keyboards import renew_kb
from app.bot.loader import get_bot
from app.bot.texts import t
from app.db.models import User, utcnow
from app.db.session import session_scope
from app.services.access import format_date_ist, get_setting, in_trial, subscription_end
from app.services.alerts import send_admin_alert
from app.services.notifier import safe_send
from app.services.payments import PaymentError, get_or_create_payment_link

logger = logging.getLogger("app.workers.reminders")


async def send_expiry_reminders() -> None:
    try:
        await _send_paid_reminders()
        await _send_trial_reminders()
    except Exception:  # noqa: BLE001
        logger.exception("send_expiry_reminders failed")
        await send_admin_alert("reminders_error", "See worker logs for the traceback.")


async def _send_paid_reminders() -> None:
    now = utcnow()
    async with session_scope() as db:
        price = int(await get_setting(db, "price_inr", 99))
        users = (
            await db.execute(select(User).where(User.status == "active"))
        ).scalars().all()
        bot = get_bot()

        for user in users:
            end = subscription_end(user)
            if end is None or end <= now:
                continue

            for days_before in (3, 1):
                window_start = end - timedelta(days=days_before)
                if window_start > now:
                    continue
                marker = f"{days_before}d:{end.date().isoformat()}"
                if user.reminder_sent_for == marker:
                    continue

                lang = user.language or "mr"
                try:
                    payment = await get_or_create_payment_link(db, user)
                except PaymentError:
                    continue
                if not payment.short_url:
                    continue

                text = t(lang, "reminder_expiring", until=format_date_ist(end))
                result = await safe_send(bot, user.telegram_id, text, renew_kb(lang, price, payment.short_url))
                if result == "blocked":
                    user.status = "bot_blocked"
                user.reminder_sent_for = marker
                break  # only the earliest matching window fires per run

        await db.commit()


async def _send_trial_reminders() -> None:
    now = utcnow()
    tomorrow = now + timedelta(days=1)
    async with session_scope() as db:
        price = int(await get_setting(db, "price_inr", 99))
        users = (
            await db.execute(
                select(User).where(
                    User.status == "active",
                    User.trial_ends_at.is_not(None),
                    User.trial_ends_at > now,
                    User.trial_ends_at <= tomorrow,
                )
            )
        ).scalars().all()
        bot = get_bot()

        for user in users:
            if not in_trial(user, now):
                continue
            marker = f"trial:{user.trial_ends_at.date().isoformat()}"
            if user.reminder_sent_for == marker:
                continue

            lang = user.language or "mr"
            try:
                payment = await get_or_create_payment_link(db, user)
            except PaymentError:
                continue
            if not payment.short_url:
                continue

            text = t(lang, "reminder_expiring", until=format_date_ist(user.trial_ends_at))
            result = await safe_send(bot, user.telegram_id, text, renew_kb(lang, price, payment.short_url))
            if result == "blocked":
                user.status = "bot_blocked"
            user.reminder_sent_for = marker

        await db.commit()
