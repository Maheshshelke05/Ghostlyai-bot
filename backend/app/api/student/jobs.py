"""GET /student/jobs - the browsable job feed (search + filter + infinite scroll), and
GET /student/jobs/{id} - single job detail. Apply tracking reuses the existing
notifier.tracking_url() + GET /r/{token} redirect unchanged.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.student.deps import current_student
from app.api.student.schemas import JobListOut, JobOut
from app.db.models import Job, JobDelivery, User
from app.db.session import get_db
from app.services.jobs import JOB_TYPES, browse_jobs_stmt, ensure_deliveries
from app.services.notifier import tracking_url

router = APIRouter(prefix="/student/jobs", tags=["student-jobs"])

DEFAULT_LIMIT = 20
MAX_LIMIT = 50


def _encode_cursor(job: Job) -> str:
    raw = f"{job.created_at.timestamp()}:{job.id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, int]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        ts_str, id_str = raw.rsplit(":", 1)
        return datetime.fromtimestamp(float(ts_str), tz=timezone.utc), int(id_str)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Invalid cursor") from exc


def _to_out(job: Job, delivery: JobDelivery) -> JobOut:
    return JobOut(
        id=job.id,
        title=job.title,
        company=job.company,
        category_id=job.category_id,
        qualification=job.qualification,
        district=job.district,
        location_text=job.location_text,
        job_type=job.job_type,
        salary=job.salary,
        description=job.description,
        last_date=job.last_date,
        created_at=job.created_at.isoformat(),
        apply_url=tracking_url(delivery.id),
        clicked=delivery.clicked_at is not None,
    )


@router.get("", response_model=JobListOut)
async def browse_jobs(
    category_id: Optional[int] = None,
    job_type: Optional[str] = None,
    q: Optional[str] = Query(default=None, max_length=100),
    cursor: Optional[str] = None,
    limit: int = Query(default=DEFAULT_LIMIT, le=MAX_LIMIT, gt=0),
    user: User = Depends(current_student),
    db: AsyncSession = Depends(get_db),
) -> JobListOut:
    if category_id is not None and category_id not in user.category_ids:
        raise HTTPException(status_code=400, detail="Not one of your selected categories")
    if job_type is not None and job_type not in JOB_TYPES:
        raise HTTPException(status_code=400, detail=f"job_type must be one of {JOB_TYPES}")

    before_created_at: Optional[datetime] = None
    before_id: Optional[int] = None
    if cursor:
        before_created_at, before_id = _decode_cursor(cursor)

    stmt = browse_jobs_stmt(
        user,
        category_id=category_id,
        job_type=job_type,
        q=q,
        before_created_at=before_created_at,
        before_id=before_id,
        limit=limit,
    )
    jobs = list((await db.execute(stmt)).scalars().all())
    deliveries = await ensure_deliveries(db, user, jobs)

    items = [_to_out(job, deliveries[job.id]) for job in jobs]
    next_cursor = _encode_cursor(jobs[-1]) if len(jobs) == limit else None
    return JobListOut(items=items, next_cursor=next_cursor)


@router.get("/{job_id}", response_model=JobOut)
async def get_job(
    job_id: int, user: User = Depends(current_student), db: AsyncSession = Depends(get_db)
) -> JobOut:
    job = await db.get(Job, job_id)
    if job is None or job.status != "active" or job.category_id not in user.category_ids:
        raise HTTPException(status_code=404, detail="Job not found")
    deliveries = await ensure_deliveries(db, user, [job])
    return _to_out(job, deliveries[job.id])
