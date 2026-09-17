"""Job CRUD, bulk upload, batch create and AI-paste drafting (Chapter 12, 17.3)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin.deps import current_admin
from app.api.admin.schemas import BatchJobsIn, JobIn
from app.config import settings as app_settings
from app.db.models import Admin, Category, Job, JobDelivery
from app.db.session import get_db
from app.services import ai
from app.services.jobs import csv_template, read_bulk_file, validate_job_row

router = APIRouter(prefix="/admin/jobs", tags=["admin-jobs"])

MAX_BULK_BYTES = 5 * 1024 * 1024


async def _categories_map(db: AsyncSession) -> dict[str, int]:
    rows = (await db.execute(select(Category.slug, Category.id))).all()
    return dict(rows)


async def _categories_name_map(db: AsyncSession) -> dict[str, str]:
    rows = (
        await db.execute(select(Category.slug, Category.name).where(Category.is_active.is_(True)))
    ).all()
    return dict(rows)


def _job_out(job: Job, sent_count: int = 0, click_count: int = 0) -> dict:
    return {
        "id": job.id, "title": job.title, "company": job.company,
        "category_id": job.category_id, "category_slug": job.category.slug if job.category else None,
        "qualification": job.qualification, "district": job.district,
        "location_text": job.location_text, "job_type": job.job_type, "salary": job.salary,
        "apply_link": job.apply_link, "last_date": job.last_date.isoformat() if job.last_date else None,
        "description": job.description,
        "status": job.status, "created_at": job.created_at.isoformat(),
        "sent_count": sent_count, "click_count": click_count,
    }


@router.get("")
async def list_jobs(
    q: Optional[str] = None,
    status: Optional[str] = None,
    category_id: Optional[int] = None,
    job_type: Optional[str] = None,
    date_filter: Optional[str] = Query(default=None, alias="date"),
    page: int = 1,
    size: int = 30,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(current_admin),
) -> dict:
    stmt = select(Job)
    if q:
        like = f"%{q}%"
        stmt = stmt.where((Job.title.ilike(like)) | (Job.company.ilike(like)))
    if status:
        stmt = stmt.where(Job.status == status)
    else:
        stmt = stmt.where(Job.status != "deleted")
    if category_id:
        stmt = stmt.where(Job.category_id == category_id)
    if job_type:
        stmt = stmt.where(Job.job_type == job_type)
    if date_filter == "today":
        start = datetime.combine(datetime.now(app_settings.tz).date(), datetime.min.time(), tzinfo=app_settings.tz)
        stmt = stmt.where(Job.created_at >= start)

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()

    stmt = stmt.order_by(Job.created_at.desc()).offset((page - 1) * size).limit(size)
    jobs = (await db.execute(stmt)).scalars().all()

    job_ids = [j.id for j in jobs]
    sent_counts: dict[int, int] = {}
    click_counts: dict[int, int] = {}
    if job_ids:
        sent_rows = (
            await db.execute(
                select(JobDelivery.job_id, func.count(JobDelivery.id))
                .where(JobDelivery.job_id.in_(job_ids)).group_by(JobDelivery.job_id)
            )
        ).all()
        sent_counts = dict(sent_rows)
        click_rows = (
            await db.execute(
                select(JobDelivery.job_id, func.count(JobDelivery.id))
                .where(JobDelivery.job_id.in_(job_ids), JobDelivery.clicked_at.is_not(None))
                .group_by(JobDelivery.job_id)
            )
        ).all()
        click_counts = dict(click_rows)

    items = [_job_out(j, sent_counts.get(j.id, 0), click_counts.get(j.id, 0)) for j in jobs]
    return {"items": items, "total": total, "page": page, "size": size}


@router.post("", status_code=201)
async def create_job(
    payload: JobIn, db: AsyncSession = Depends(get_db), admin: Admin = Depends(current_admin)
) -> dict:
    categories = await _categories_map(db)
    try:
        kwargs = validate_job_row(payload.model_dump(), categories)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    job = Job(admin_id=admin.id, **kwargs)
    db.add(job)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="A job with the same title/company/link already exists")

    await db.refresh(job, attribute_names=["category"])
    return _job_out(job)


@router.get("/bulk/template")
async def bulk_template(_admin=Depends(current_admin)) -> Response:
    return Response(
        content=csv_template(), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=jobs_template.csv"},
    )


@router.get("/{job_id}")
async def get_job(job_id: int, db: AsyncSession = Depends(get_db), _admin=Depends(current_admin)) -> dict:
    job = await db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    sent_count = (
        await db.execute(select(func.count(JobDelivery.id)).where(JobDelivery.job_id == job_id))
    ).scalar_one()
    click_count = (
        await db.execute(
            select(func.count(JobDelivery.id)).where(
                JobDelivery.job_id == job_id, JobDelivery.clicked_at.is_not(None)
            )
        )
    ).scalar_one()
    return _job_out(job, sent_count, click_count)


@router.put("/{job_id}")
async def update_job(
    job_id: int, payload: JobIn, db: AsyncSession = Depends(get_db), _admin=Depends(current_admin)
) -> dict:
    job = await db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    categories = await _categories_map(db)
    try:
        kwargs = validate_job_row(payload.model_dump(), categories)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    new_fingerprint = kwargs["fingerprint"]
    if new_fingerprint != job.fingerprint:
        clash = (
            await db.execute(select(Job).where(Job.fingerprint == new_fingerprint, Job.id != job_id))
        ).scalar_one_or_none()
        if clash is not None:
            raise HTTPException(status_code=409, detail="Another job already has this title/company/link")

    for key, value in kwargs.items():
        setattr(job, key, value)
    await db.flush()
    await db.refresh(job, attribute_names=["category"])
    return _job_out(job)


@router.delete("/{job_id}")
async def delete_job(job_id: int, db: AsyncSession = Depends(get_db), _admin=Depends(current_admin)) -> dict:
    job = await db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = "deleted"
    await db.flush()
    return {"ok": True}


@router.post("/batch")
async def batch_create(
    payload: BatchJobsIn, db: AsyncSession = Depends(get_db), admin: Admin = Depends(current_admin)
) -> dict:
    categories = await _categories_map(db)
    rows = []
    errors: list[dict] = []
    for index, job_in in enumerate(payload.jobs):
        try:
            rows.append(validate_job_row(job_in.model_dump(), categories))
        except ValueError as exc:
            errors.append({"index": index, "error": str(exc)})

    created, duplicates = await _insert_new_jobs(db, admin, rows)
    return {"created": created, "duplicates": duplicates, "errors": errors}


async def _insert_new_jobs(db: AsyncSession, admin: Admin, rows: list[dict]) -> tuple[int, int]:
    """Adds rows whose fingerprint isn't already in the DB *or earlier in this same batch*.

    The session runs with autoflush off, so a pending (unflushed) row is invisible to the
    per-row existence query - two identical rows in one upload used to both get added and
    blow up the whole request on the unique constraint at flush time.
    """
    seen: set[str] = set()
    created = duplicates = 0
    for kwargs in rows:
        fp = kwargs["fingerprint"]
        if fp in seen:
            duplicates += 1
            continue
        seen.add(fp)
        existing = (await db.execute(select(Job.id).where(Job.fingerprint == fp))).scalar_one_or_none()
        if existing is not None:
            duplicates += 1
            continue
        db.add(Job(admin_id=admin.id, **kwargs))
        created += 1

    try:
        await db.flush()
    except IntegrityError:
        # another upload inserted one of these between our check and the flush
        await db.rollback()
        raise HTTPException(
            status_code=409, detail="Some of these jobs were added at the same time by another upload. Please retry."
        )
    return created, duplicates


@router.post("/bulk")
async def bulk_upload(
    file: UploadFile, db: AsyncSession = Depends(get_db), admin: Admin = Depends(current_admin)
) -> dict:
    data = await file.read()
    if len(data) > MAX_BULK_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 5 MB)")

    try:
        rows = read_bulk_file(file.filename or "", data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    categories = await _categories_map(db)
    valid = []
    errors: list[dict] = []
    for row_number, raw_row in rows:
        try:
            valid.append(validate_job_row(raw_row, categories))
        except ValueError as exc:
            errors.append({"row": row_number, "error": str(exc)})

    created, duplicates = await _insert_new_jobs(db, admin, valid)
    return {"created": created, "duplicates": duplicates, "errors": errors}


@router.post("/ai-parse")
async def ai_parse(
    payload: dict, db: AsyncSession = Depends(get_db), _admin=Depends(current_admin)
) -> dict:
    text = str(payload.get("text") or "")
    if not text.strip():
        raise HTTPException(status_code=422, detail="text is required")

    categories = await _categories_name_map(db)
    drafts = await ai.parse_job_text(text, categories)
    return {"drafts": [d.model_dump() for d in drafts]}
