"""Job validation, fingerprinting, bulk file reading and the matching query (Chapter 10, 12)."""
from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta
from typing import Any, Optional

import openpyxl
from sqlalchemy import and_, exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Job, JobDelivery, User, utcnow

JOB_TYPES = ("govt", "private", "internship", "wfh")

REQUIRED_FIELDS = ("title", "company", "category_slug", "apply_link")
BULK_COLUMNS = (
    "title", "company", "category_slug", "qualification", "location_text",
    "job_type", "salary", "apply_link", "last_date", "description",
)

_DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y")


def fingerprint(title: str, company: str, apply_link: str) -> str:
    return Job.make_fingerprint(title, company, apply_link)


def parse_date(value: str | date | None) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    if not text:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognised date format: {value!r}")


def validate_job_row(row: dict[str, Any], categories: dict[str, int]) -> dict[str, Any]:
    """Validate/clean a raw job row into Job() kwargs, or raise ValueError with a readable message."""
    title = str(row.get("title") or "").strip()
    if not (2 <= len(title) <= 200):
        raise ValueError("title must be 2-200 characters")

    company = str(row.get("company") or "").strip()
    if not (1 <= len(company) <= 160):
        raise ValueError("company must be 1-160 characters")

    category_slug = str(row.get("category_slug") or "").strip()
    if category_slug not in categories:
        raise ValueError(f"unknown category_slug: {category_slug!r}")

    apply_link = str(row.get("apply_link") or "").strip()
    if not (apply_link.startswith("http://") or apply_link.startswith("https://")):
        raise ValueError("apply_link must be a valid http(s) URL")
    if len(apply_link) > 500:
        raise ValueError("apply_link too long")

    job_type = str(row.get("job_type") or "private").strip().lower() or "private"
    if job_type not in JOB_TYPES:
        raise ValueError(f"job_type must be one of {JOB_TYPES}")

    last_date_raw = row.get("last_date")
    try:
        last_date = parse_date(last_date_raw)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    qualification = str(row.get("qualification") or "").strip()[:200] or None
    location_text = str(row.get("location_text") or "").strip()[:160] or None
    salary = str(row.get("salary") or "").strip()[:80] or None
    description = str(row.get("description") or "").strip()[:1000] or None

    return {
        "category_id": categories[category_slug],
        "title": title,
        "company": company,
        "qualification": qualification,
        "location_text": location_text,
        "job_type": job_type,
        "salary": salary,
        "description": description,
        "apply_link": apply_link,
        "last_date": last_date,
        "fingerprint": fingerprint(title, company, apply_link),
    }


def read_bulk_file(filename: str, data: bytes) -> list[tuple[int, dict[str, Any]]]:
    """Returns [(row_number, raw_row_dict), ...] with 1-based row numbers (header = row 1)."""
    lower = filename.lower()
    if lower.endswith(".csv"):
        return _read_csv(data)
    if lower.endswith(".xlsx"):
        return _read_xlsx(data)
    raise ValueError("Only .csv and .xlsx files are supported")


def _read_csv(data: bytes) -> list[tuple[int, dict[str, Any]]]:
    text = data.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rows: list[tuple[int, dict[str, Any]]] = []
    for i, row in enumerate(reader, start=2):  # row 1 is the header
        rows.append((i, row))
    return rows


def _read_xlsx(data: bytes) -> list[tuple[int, dict[str, Any]]]:
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    header = [str(h).strip() if h is not None else "" for h in next(rows_iter, [])]
    rows: list[tuple[int, dict[str, Any]]] = []
    for i, values in enumerate(rows_iter, start=2):
        row = {header[j]: values[j] for j in range(min(len(header), len(values)))}
        if not any(v not in (None, "") for v in row.values()):
            continue
        rows.append((i, row))
    return rows


def csv_template() -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(BULK_COLUMNS)
    writer.writerow([
        "Junior Accountant", "Shree Traders Pvt Ltd", "accounts-finance", "B.Com, Tally",
        "Sitabuldi, Nagpur", "private", "₹12,000 – ₹15,000",
        "https://example.com/apply/123", "30-09-2026", "2 openings, Saturday half day",
    ])
    return output.getvalue().encode("utf-8-sig")


def matching_jobs_stmt(user: User, limit: int, days_window: int = 7, min_age_minutes: int = 0):
    """SQLAlchemy select() for jobs matching a user, newest first (Chapter 10.1).

    `min_age_minutes` holds a freshly uploaded job back for a while, so an admin has time to
    spot a typo or a wrong link before it reaches students.
    """
    now = utcnow()
    since = now - timedelta(days=days_window)

    category_ids = [uc.category_id for uc in user.category_links]
    if not category_ids:
        return select(Job).where(Job.id.is_(None))  # no categories -> no matches

    conditions = [
        Job.status == "active",
        Job.category_id.in_(category_ids),
        Job.created_at > since,
        or_(Job.last_date.is_(None), Job.last_date >= today_ist()),
        ~exists().where(and_(JobDelivery.job_id == Job.id, JobDelivery.user_id == user.id)),
    ]
    if user.job_types:
        conditions.append(Job.job_type.in_(user.job_types))
    if min_age_minutes > 0:
        conditions.append(Job.created_at <= now - timedelta(minutes=min_age_minutes))

    stmt = (
        select(Job)
        .where(and_(*conditions))
        .order_by(Job.created_at.desc())
        .limit(limit)
    )
    return stmt


def browse_jobs_stmt(
    user: User,
    *,
    category_id: Optional[int] = None,
    job_type: Optional[str] = None,
    district: Optional[str] = None,
    q: Optional[str] = None,
    days_window: int = 7,
    before_created_at: Optional[datetime] = None,
    before_id: Optional[int] = None,
    limit: int = 20,
):
    """SQLAlchemy select() for the app's browsable job feed.

    Sibling to matching_jobs_stmt(), same category/job-type/last-date/recency rules, but
    deliberately does NOT anti-join JobDelivery - a feed the student can scroll and re-open
    should keep showing jobs they've already seen, unlike a one-shot digest. Supports the
    home screen's search box and filter button as explicit overrides/narrowing on top of the
    student's own saved categories (this never lets a student browse outside the categories
    they picked - that's the product's subscription boundary, not just a UI default).
    """
    now = utcnow()
    since = now - timedelta(days=days_window)

    category_ids = [uc.category_id for uc in user.category_links]
    if not category_ids:
        return select(Job).where(Job.id.is_(None))

    conditions = [
        Job.status == "active",
        Job.category_id.in_(category_ids),
        Job.created_at > since,
        or_(Job.last_date.is_(None), Job.last_date >= today_ist()),
    ]

    if category_id is not None:
        conditions.append(Job.category_id == category_id)

    if job_type:
        conditions.append(Job.job_type == job_type)
    elif user.job_types:
        conditions.append(Job.job_type.in_(user.job_types))

    if district:
        conditions.append(or_(Job.district.is_(None), Job.district == district, Job.job_type == "wfh"))

    if q:
        like = f"%{q.strip()}%"
        conditions.append(
            or_(Job.title.ilike(like), Job.company.ilike(like), Job.location_text.ilike(like))
        )

    if before_created_at is not None and before_id is not None:
        conditions.append(
            or_(
                Job.created_at < before_created_at,
                and_(Job.created_at == before_created_at, Job.id < before_id),
            )
        )

    return (
        select(Job)
        .where(and_(*conditions))
        .order_by(Job.created_at.desc(), Job.id.desc())
        .limit(limit)
    )


async def ensure_deliveries(
    db: AsyncSession, user: User, jobs: list[Job]
) -> dict[int, JobDelivery]:
    """Batch get-or-creates JobDelivery rows for a page of browsed jobs, so each can get a
    tracking_url() and so a job already seen in-app is correctly excluded from future push
    "what's new" notifications (they share the same delivery ledger as the Telegram digest)."""
    if not jobs:
        return {}
    job_ids = [job.id for job in jobs]
    existing = (
        await db.execute(
            select(JobDelivery).where(
                JobDelivery.user_id == user.id, JobDelivery.job_id.in_(job_ids)
            )
        )
    ).scalars().all()
    by_job_id = {d.job_id: d for d in existing}
    for job in jobs:
        if job.id not in by_job_id:
            delivery = JobDelivery(job_id=job.id, user_id=user.id)
            db.add(delivery)
            by_job_id[job.id] = delivery
    await db.flush()
    return by_job_id


def today_ist() -> date:
    from app.config import settings

    return datetime.now(settings.tz).date()


async def job_delay_minutes(db: AsyncSession) -> int:
    from app.services.access import get_setting

    return int(await get_setting(db, "job_delay_minutes", 90))


async def matching_jobs(db: AsyncSession, user: User, limit: int) -> list[Job]:
    stmt = matching_jobs_stmt(user, limit, min_age_minutes=await job_delay_minutes(db))
    return list((await db.execute(stmt)).scalars().all())
