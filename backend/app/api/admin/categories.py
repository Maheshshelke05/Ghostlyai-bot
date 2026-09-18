"""Category CRUD (Chapter 17.5). Slug is immutable once created."""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin.deps import current_admin, owner_only
from app.api.admin.schemas import CategoryIn, CategoryUpdate
from app.db.models import Category, Job, JobDelivery, User, UserCategory, utcnow
from app.db.session import get_db
from app.services import cache
from app.services.jobs import job_delay_minutes

router = APIRouter(prefix="/admin/categories", tags=["admin-categories"])


@router.get("")
async def list_categories(db: AsyncSession = Depends(get_db), _admin=Depends(current_admin)) -> list[dict]:
    categories = (
        await db.execute(select(Category).order_by(Category.sort_order, Category.id))
    ).scalars().all()

    users_counts = dict(
        (await db.execute(
            select(UserCategory.category_id, func.count(UserCategory.user_id)).group_by(UserCategory.category_id)
        )).all()
    )
    jobs_counts = dict(
        (await db.execute(
            select(Job.category_id, func.count(Job.id)).where(Job.status == "active").group_by(Job.category_id)
        )).all()
    )

    return [
        {
            "id": c.id, "slug": c.slug, "name": c.name, "name_mr": c.name_mr, "name_hi": c.name_hi,
            "is_active": c.is_active, "sort_order": c.sort_order,
            "users_count": users_counts.get(c.id, 0), "jobs_count": jobs_counts.get(c.id, 0),
        }
        for c in categories
    ]


@router.get("/delivery-stats")
async def delivery_stats(
    days: int = 7, db: AsyncSession = Depends(get_db), _admin=Depends(current_admin)
) -> dict:
    """Per category: jobs added, how many were delivered, and how many students are still
    waiting - i.e. subscribers who have a matching job that hasn't reached them yet."""
    days = max(1, min(days, 90))
    return await cache.get_or_set(
        f"admin:delivery-stats:{days}", ttl_seconds=20, compute=lambda: _compute_delivery_stats(db, days)
    )


async def _compute_delivery_stats(db: AsyncSession, days: int) -> dict:
    since = utcnow() - timedelta(days=days)
    delay = await job_delay_minutes(db)
    ready_before = utcnow() - timedelta(minutes=delay)

    categories = (
        await db.execute(select(Category).order_by(Category.sort_order, Category.id))
    ).scalars().all()

    jobs_rows = (await db.execute(
        select(Job.category_id, func.count(Job.id))
        .where(Job.status == "active", Job.created_at >= since)
        .group_by(Job.category_id)
    )).all()
    pending_rows = (await db.execute(
        select(Job.category_id, func.count(Job.id))
        .where(Job.status == "active", Job.created_at >= since, Job.created_at > ready_before)
        .group_by(Job.category_id)
    )).all()
    sent_rows = (await db.execute(
        select(Job.category_id, func.count(JobDelivery.id))
        .join(JobDelivery, JobDelivery.job_id == Job.id)
        .where(Job.created_at >= since)
        .group_by(Job.category_id)
    )).all()
    clicked_rows = (await db.execute(
        select(Job.category_id, func.count(JobDelivery.id))
        .join(JobDelivery, JobDelivery.job_id == Job.id)
        .where(Job.created_at >= since, JobDelivery.clicked_at.is_not(None))
        .group_by(Job.category_id)
    )).all()
    subscribers_rows = (await db.execute(
        select(UserCategory.category_id, func.count(UserCategory.user_id))
        .join(User, User.id == UserCategory.user_id)
        .where(User.status == "active")
        .group_by(UserCategory.category_id)
    )).all()
    # Students subscribed to a category who still have an undelivered ready job, grouped in one
    # query instead of one extra round-trip per category (this used to be O(categories) queries -
    # 21 categories meant 21 extra sequential round-trips to the database on every dashboard load).
    waiting_rows = (await db.execute(
        select(UserCategory.category_id, func.count(func.distinct(UserCategory.user_id)))
        .select_from(UserCategory)
        .join(User, User.id == UserCategory.user_id)
        .join(Job, Job.category_id == UserCategory.category_id)
        .where(
            User.status == "active",
            Job.status == "active",
            Job.created_at >= since,
            Job.created_at <= ready_before,
            ~exists().where(and_(JobDelivery.job_id == Job.id, JobDelivery.user_id == User.id)),
        )
        .group_by(UserCategory.category_id)
    )).all()

    jobs_map, pending_map = dict(jobs_rows), dict(pending_rows)
    sent_map, clicked_map, subs_map = dict(sent_rows), dict(clicked_rows), dict(subscribers_rows)
    waiting_map = dict(waiting_rows)

    items = [
        {
            "category_id": c.id, "slug": c.slug, "name": c.name, "is_active": c.is_active,
            "jobs": jobs_map.get(c.id, 0),
            "jobs_waiting_to_send": pending_map.get(c.id, 0),
            "subscribers": subs_map.get(c.id, 0),
            "sent": sent_map.get(c.id, 0),
            "clicked": clicked_map.get(c.id, 0),
            "students_waiting": waiting_map.get(c.id, 0),
        }
        for c in categories
    ]

    return {"days": days, "job_delay_minutes": delay, "items": items}


@router.post("")
async def create_category(
    payload: CategoryIn, db: AsyncSession = Depends(get_db), _admin=Depends(owner_only)
) -> dict:
    existing = (
        await db.execute(select(Category).where(Category.slug == payload.slug))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Category slug already exists")

    category = Category(**payload.model_dump())
    db.add(category)
    await db.flush()
    return {"id": category.id, "slug": category.slug}


@router.put("/{category_id}")
async def update_category(
    category_id: int, payload: CategoryUpdate,
    db: AsyncSession = Depends(get_db), _admin=Depends(owner_only),
) -> dict:
    category = await db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(category, key, value)
    await db.flush()
    return {"ok": True}
