"""Sending messages safely, formatting job cards, digest delivery, click tracking (Chapter 10)."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import html
import logging
from datetime import date

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import apply_kb
from app.bot.texts import t
from app.config import settings
from app.db.models import Job, JobDelivery, User, utcnow
from app.services.jobs import matching_jobs, matching_jobs_stmt

logger = logging.getLogger("app.notifier")

_MESSAGE_DELAY = 0.05  # ~20 msg/sec, inside Telegram broadcast limits
_JOBS_PER_MESSAGE = 5
_MAX_RETRIES = 3

_TRUNCATE = {"title": 90, "company": 60, "location": 50, "qualification": 80, "salary": 40}


def _truncate(value: str | None, field: str) -> str:
    if not value:
        return ""
    limit = _TRUNCATE[field]
    value = value.strip()
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"


def _fmt_date(d: date) -> str:
    return d.strftime("%d-%m-%Y")


def format_job_card(job: Job, n: int, lang: str) -> str:
    location = job.location_text or job.district or t(lang, "any_location")
    job_type_label = {
        "govt": t(lang, "jt_govt"), "private": t(lang, "jt_private"),
        "internship": t(lang, "jt_internship"), "wfh": t(lang, "jt_wfh"),
    }.get(job.job_type, job.job_type)

    qualification_part = (
        t(lang, "qualification_part", qualification=html.escape(_truncate(job.qualification, "qualification")))
        if job.qualification else ""
    )
    salary_part = t(lang, "salary_part", salary=html.escape(_truncate(job.salary, "salary"))) if job.salary else ""
    last_date_part = t(lang, "last_date_part", date=_fmt_date(job.last_date)) if job.last_date else ""

    return t(
        lang, "job_line",
        n=n,
        title=html.escape(_truncate(job.title, "title")),
        company=html.escape(_truncate(job.company, "company")),
        location=html.escape(_truncate(location, "location")),
        job_type=job_type_label,
        qualification=qualification_part,
        salary=salary_part,
        last_date=last_date_part,
    ).rstrip()


def tracking_url(delivery_id: int) -> str:
    sig = _sign(delivery_id)
    return f"{settings.BASE_URL.rstrip('/')}/r/{delivery_id}-{sig}"


def _sign(delivery_id: int) -> str:
    digest = hmac.new(
        settings.JWT_SECRET.encode("utf-8"), str(delivery_id).encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return digest[:10]


def parse_tracking_token(token: str) -> int | None:
    if "-" not in token:
        return None
    id_part, sig_part = token.rsplit("-", 1)
    if not id_part.isdigit():
        return None
    delivery_id = int(id_part)
    expected = _sign(delivery_id)
    if not hmac.compare_digest(expected, sig_part):
        return None
    return delivery_id


async def safe_send(bot: Bot, chat_id: int, text: str, markup=None) -> str:
    """Returns "ok" | "blocked" | "error"."""
    for attempt in range(_MAX_RETRIES):
        try:
            await bot.send_message(
                chat_id, text, reply_markup=markup, disable_web_page_preview=True
            )
            return "ok"
        except TelegramRetryAfter as exc:
            await asyncio.sleep(exc.retry_after + 1)
        except TelegramForbiddenError:
            return "blocked"
        except TelegramBadRequest:
            logger.warning("Telegram BadRequest sending to %s", chat_id, exc_info=True)
            return "error"
        except Exception:  # noqa: BLE001
            logger.warning("Telegram send error to %s (attempt %s)", chat_id, attempt + 1, exc_info=True)
            await asyncio.sleep(2)
    return "error"


async def count_matching_jobs(db: AsyncSession, user: User, limit: int = 100) -> int:
    stmt = matching_jobs_stmt(user, limit)
    rows = (await db.execute(stmt)).scalars().all()
    return len(rows)


async def send_digest_to_user(db: AsyncSession, bot: Bot, user: User, limit: int) -> int:
    """Sends up to `limit` new matching jobs to a user. Returns count of jobs actually sent."""
    jobs = await matching_jobs(db, user, limit)
    if not jobs:
        return 0

    lang = user.language or "mr"
    deliveries: list[JobDelivery] = []
    for job in jobs:
        delivery = JobDelivery(job_id=job.id, user_id=user.id)
        db.add(delivery)
        deliveries.append(delivery)
    await db.flush()

    header = t(lang, "digest_header", count=len(jobs))
    sent_any = False
    blocked = False

    for chunk_start in range(0, len(jobs), _JOBS_PER_MESSAGE):
        chunk_jobs = jobs[chunk_start:chunk_start + _JOBS_PER_MESSAGE]
        chunk_deliveries = deliveries[chunk_start:chunk_start + _JOBS_PER_MESSAGE]
        lines = [format_job_card(job, chunk_start + i + 1, lang) for i, job in enumerate(chunk_jobs)]
        text = "\n\n".join(lines)
        if chunk_start == 0:
            text = f"{header}\n\n{text}"

        buttons = [
            (chunk_start + i + 1, tracking_url(delivery.id))
            for i, delivery in enumerate(chunk_deliveries)
        ]
        markup = apply_kb(buttons)

        result = await safe_send(bot, user.telegram_id, text, markup)
        if result == "ok":
            sent_any = True
        elif result == "blocked":
            blocked = True
            break
        await asyncio.sleep(_MESSAGE_DELAY)

    if blocked:
        user.status = "bot_blocked"

    if not sent_any:
        for delivery in deliveries:
            await db.delete(delivery)
        await db.flush()
        return 0

    user.last_digest_at = utcnow()
    await db.flush()
    return len(jobs)
