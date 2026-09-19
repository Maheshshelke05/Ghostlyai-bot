"""Push notifications for new matching jobs, for students using the app.

Sibling to workers/digest.py's frequent-interval Telegram digest, running on the same cadence
(see scheduler.py) so both channels feel equally near-instant. Reuses the exact same
matching_jobs_stmt() as the Telegram digest, so a job already delivered via Telegram - or
already seen in the app's browsable feed, since both write to the same job_deliveries ledger
via services/jobs.py::ensure_deliveries() - is correctly excluded here too.
"""
from __future__ import annotations

import logging

from sqlalchemy import select

from app.db.models import User, utcnow
from app.db.session import session_scope
from app.services.access import has_access
from app.services.jobs import ensure_deliveries, job_delay_minutes, matching_jobs_stmt
from app.services.push import send_push_to_student

logger = logging.getLogger("app.workers.push_digest")

_BATCH_SIZE = 500
_JOBS_PER_PUSH = 10


async def run_push_digest() -> None:
    total_users = 0
    total_pushed = 0
    started = utcnow()

    last_id = 0
    while True:
        async with session_scope() as db:
            users = (
                await db.execute(
                    select(User)
                    .where(
                        User.status == "active",
                        User.expo_push_token.is_not(None),
                        User.id > last_id,
                    )
                    .order_by(User.id)
                    .limit(_BATCH_SIZE)
                )
            ).scalars().all()

            if not users:
                break

            delay = await job_delay_minutes(db)
            for user in users:
                last_id = user.id
                total_users += 1
                try:
                    if not has_access(user):
                        continue
                    stmt = matching_jobs_stmt(user, limit=_JOBS_PER_PUSH, min_age_minutes=delay)
                    jobs = list((await db.execute(stmt)).scalars().all())
                    if not jobs:
                        continue

                    await ensure_deliveries(db, user, jobs)

                    if len(jobs) == 1:
                        title = "1 new job matches your profile"
                        body = f"{jobs[0].title} — {jobs[0].company}"
                    else:
                        title = f"{len(jobs)} new jobs match your profile"
                        body = f"{jobs[0].title} and {len(jobs) - 1} more"
                    await send_push_to_student(user, title, body, {"type": "jobs"})
                    total_pushed += 1
                except Exception:  # noqa: BLE001
                    logger.exception("Error sending push digest to user %s", user.id)

            await db.commit()

    duration = (utcnow() - started).total_seconds()
    logger.info(
        "run_push_digest done: users=%s pushed=%s duration=%.1fs",
        total_users, total_pushed, duration,
    )
