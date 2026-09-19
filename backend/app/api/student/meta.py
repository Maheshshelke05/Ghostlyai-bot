"""Public reference data for the student app: categories, price/trial settings.

Unauthenticated on purpose - none of this is sensitive (the bot shows the same categories to
anyone who starts onboarding), and the welcome/login screens need price/trial copy before a
student has logged in at all. No districts endpoint - the app doesn't collect district
(see CLAUDE.md BUSINESS RULES); the Telegram bot's own onboarding still uses
app/services/districts.py directly.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.student.schemas import CategoryOut, SettingsOut
from app.db.models import Category
from app.db.session import get_db
from app.services.access import get_all_settings

router = APIRouter(prefix="/student", tags=["student-meta"])


@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(lang: str = "mr", db: AsyncSession = Depends(get_db)) -> list[CategoryOut]:
    rows = (
        await db.execute(
            select(Category).where(Category.is_active.is_(True)).order_by(Category.sort_order)
        )
    ).scalars().all()
    return [CategoryOut(id=c.id, slug=c.slug, name=c.label(lang)) for c in rows]


@router.get("/settings", response_model=SettingsOut)
async def public_settings(db: AsyncSession = Depends(get_db)) -> SettingsOut:
    settings_map = await get_all_settings(db)
    return SettingsOut(
        price_inr=int(settings_map.get("price_inr", 99)),
        subscription_days=int(settings_map.get("subscription_days", 30)),
        trial_days=int(settings_map.get("trial_days", 3)),
        max_categories=int(settings_map.get("max_categories", 3)),
    )
