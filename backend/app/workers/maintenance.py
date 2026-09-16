"""Job expiry, payment link expiry and data retention cleanup (Chapter 16.3, 18)."""
from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy import delete, update

from app.db.models import Job, JobDelivery, Payment, utcnow
from app.db.session import session_scope
from app.services.alerts import send_admin_alert
from app.services.jobs import today_ist

logger = logging.getLogger("app.workers.maintenance")


async def expire_jobs() -> None:
    try:
        async with session_scope() as db:
            result = await db.execute(
                update(Job)
                .where(Job.status == "active", Job.last_date.is_not(None), Job.last_date < today_ist())
                .values(status="expired")
            )
            await db.commit()
            if result.rowcount:
                logger.info("expire_jobs: marked %s jobs expired", result.rowcount)
    except Exception:  # noqa: BLE001
        logger.exception("expire_jobs failed")
        await send_admin_alert("expire_jobs_error", "See worker logs for the traceback.")


async def expire_payment_links() -> None:
    try:
        async with session_scope() as db:
            result = await db.execute(
                update(Payment)
                .where(Payment.status == "created", Payment.expires_at < utcnow())
                .values(status="expired")
            )
            await db.commit()
            if result.rowcount:
                logger.info("expire_payment_links: marked %s payments expired", result.rowcount)
    except Exception:  # noqa: BLE001
        logger.exception("expire_payment_links failed")
        await send_admin_alert("expire_payment_links_error", "See worker logs for the traceback.")


async def cleanup_retention() -> None:
    """Weekly retention pass (Chapter 16.3)."""
    now = utcnow()
    try:
        async with session_scope() as db:
            await db.execute(delete(JobDelivery).where(JobDelivery.sent_at < now - timedelta(days=90)))
            await db.execute(
                delete(Job).where(Job.status == "expired", Job.created_at < now - timedelta(days=180))
            )
            await db.execute(
                delete(Payment).where(Payment.status == "created", Payment.created_at < now - timedelta(days=30))
            )
            await db.commit()
            logger.info("cleanup_retention: done")
    except Exception:  # noqa: BLE001
        logger.exception("cleanup_retention failed")
        await send_admin_alert("cleanup_retention_error", "See worker logs for the traceback.")
