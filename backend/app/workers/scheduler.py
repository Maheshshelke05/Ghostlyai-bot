"""Worker process entrypoint: registers all scheduled jobs and runs forever.

Usage: python -m app.workers.scheduler
"""
from __future__ import annotations

import asyncio
import logging
import signal

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.workers.broadcast import broadcast_runner
from app.workers.digest import digest_tick
from app.workers.ghostly_alerts import ghostly_alerts_tick
from app.workers.maintenance import cleanup_retention, expire_jobs, expire_payment_links
from app.workers.push_digest import run_push_digest
from app.workers.reminders import send_expiry_reminders

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("app.workers.scheduler")

TZ = "Asia/Kolkata"


def build_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=TZ)

    scheduler.add_job(
        digest_tick, CronTrigger(minute="*/2", timezone=TZ), id="digest_tick", max_instances=1
    )
    scheduler.add_job(
        send_expiry_reminders, CronTrigger(hour=10, minute=0, timezone=TZ),
        id="expiry_reminders", max_instances=1,
    )
    scheduler.add_job(
        expire_jobs, CronTrigger(hour=0, minute=5, timezone=TZ), id="expire_jobs", max_instances=1
    )
    scheduler.add_job(
        expire_payment_links, CronTrigger(minute=0, timezone=TZ),
        id="expire_payment_links", max_instances=1,
    )
    scheduler.add_job(
        broadcast_runner, CronTrigger(second="*/30", timezone=TZ),
        id="broadcast_runner", max_instances=1,
    )
    scheduler.add_job(
        cleanup_retention, CronTrigger(day_of_week="sun", hour=3, minute=0, timezone=TZ),
        id="cleanup_retention", max_instances=1,
    )
    scheduler.add_job(
        ghostly_alerts_tick, CronTrigger(minute="*/5", timezone=TZ),
        id="ghostly_alerts_tick", max_instances=1,
    )
    scheduler.add_job(
        run_push_digest, CronTrigger(minute="*/2", timezone=TZ),
        id="push_digest", max_instances=1,
    )
    return scheduler


async def main() -> None:
    scheduler = build_scheduler()
    scheduler.start()
    logger.info("Worker scheduler started (timezone=%s)", TZ)

    stop_event = asyncio.Event()

    def _handle_stop(*_args) -> None:
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_stop)
        except NotImplementedError:
            pass  # Windows does not support add_signal_handler for SIGTERM

    await stop_event.wait()
    scheduler.shutdown(wait=False)
    logger.info("Worker scheduler stopped")


if __name__ == "__main__":
    asyncio.run(main())
