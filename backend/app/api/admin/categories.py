"""Category CRUD (Chapter 17.5). Slug is immutable once created."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin.deps import current_admin, owner_only
from app.api.admin.schemas import CategoryIn, CategoryUpdate
from app.db.models import Category, Job, UserCategory
from app.db.session import get_db

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
