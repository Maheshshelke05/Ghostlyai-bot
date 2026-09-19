"""Onboarding endpoints for the student app: name -> district -> resume (optional) ->
complete (categories + job types) - mirrors backend/app/bot/handlers/onboarding.py step-by-step,
one API-friendly step at a time instead of aiogram's FSM.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.student.auth import next_step, to_out
from app.api.student.deps import current_student
from app.api.student.schemas import (
    CompleteOnboardingIn,
    DistrictIn,
    MeOut,
    NameIn,
    PushTokenIn,
    ResumeSummaryOut,
)
from app.config import settings
from app.db.models import Category, Profile, User, UserCategory
from app.db.session import get_db
from app.services import ai, storage
from app.services.access import get_setting, start_trial
from app.services.districts import canonical_district
from app.services.jobs import JOB_TYPES
from app.services.push import send_push_to_admins
from app.services.validators import normalize_name, valid_name

router = APIRouter(prefix="/student/me", tags=["student-onboarding"])

_RESUME_MIME_BY_EXT = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}
_SUPPORTED_RESUME_MIMES = set(_RESUME_MIME_BY_EXT.values())


async def _active_categories(db: AsyncSession) -> list[Category]:
    rows = (
        await db.execute(
            select(Category).where(Category.is_active.is_(True)).order_by(Category.sort_order)
        )
    ).scalars().all()
    return list(rows)


@router.put("/name", response_model=MeOut)
async def set_name(
    payload: NameIn, user: User = Depends(current_student), db: AsyncSession = Depends(get_db)
) -> MeOut:
    text = payload.full_name.strip()
    if not valid_name(text):
        raise HTTPException(status_code=400, detail="Enter your full name (first and last name)")
    user.full_name = normalize_name(text)
    await db.flush()
    return MeOut(user=to_out(user), next_step=next_step(user))


@router.put("/district", response_model=MeOut)
async def set_district(
    payload: DistrictIn, user: User = Depends(current_student), db: AsyncSession = Depends(get_db)
) -> MeOut:
    text = payload.district.strip()
    canon = canonical_district(text)
    user.district = canon if canon else text.title()[:60]
    await db.flush()
    return MeOut(user=to_out(user), next_step=next_step(user))


@router.post("/resume", response_model=ResumeSummaryOut)
async def upload_resume(
    file: UploadFile = File(...),
    user: User = Depends(current_student),
    db: AsyncSession = Depends(get_db),
) -> ResumeSummaryOut:
    filename = file.filename or ""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    mime = file.content_type or ""
    resolved_mime = mime if mime in _SUPPORTED_RESUME_MIMES else _RESUME_MIME_BY_EXT.get(ext)
    if resolved_mime is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Use PDF, DOCX or a photo (max {settings.MAX_RESUME_MB}MB).",
        )

    data = await file.read()
    max_bytes = settings.MAX_RESUME_MB * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(status_code=400, detail=f"File too large. Max {settings.MAX_RESUME_MB}MB.")

    categories = {c.slug: c.name for c in await _active_categories(db)}
    result = await ai.parse_resume(data, resolved_mime, categories)
    if result is None:
        raise HTTPException(status_code=422, detail="Could not read this file. Try a clearer PDF or photo.")
    if not result.is_resume:
        raise HTTPException(status_code=422, detail="This doesn't look like a resume.")

    profile = user.profile
    path = await storage.save_resume(
        user.id, data, resolved_mime, filename,
        previous_resume_path=profile.resume_path if profile else None,
    )
    if profile is None:
        profile = Profile(user_id=user.id)
        db.add(profile)
        user.profile = profile

    profile.education = result.highest_education
    profile.course = result.course
    profile.skills = result.skills
    profile.experience_years = result.experience_years or 0
    profile.summary = result.summary
    profile.resume_path = path
    profile.resume_mime = resolved_mime
    profile.parsed_json = result.model_dump()
    await db.flush()

    if not user.district and result.city_or_district:
        canon = canonical_district(result.city_or_district)
        user.district = canon if canon else result.city_or_district.title()
        await db.flush()

    return ResumeSummaryOut(
        education=profile.education,
        course=profile.course,
        skills=profile.skills,
        experience_years=float(profile.experience_years or 0),
        summary=profile.summary,
        suggested_category_slugs=result.suggested_category_slugs,
    )


@router.post("/complete", response_model=MeOut)
async def complete_onboarding(
    payload: CompleteOnboardingIn,
    user: User = Depends(current_student),
    db: AsyncSession = Depends(get_db),
) -> MeOut:
    if not user.full_name:
        raise HTTPException(status_code=400, detail="Name is required first")
    if not user.district:
        raise HTTPException(status_code=400, detail="District is required first")

    max_categories = int(await get_setting(db, "max_categories", 3))
    if not (1 <= len(payload.category_ids) <= max_categories):
        raise HTTPException(status_code=400, detail=f"Pick 1 to {max_categories} categories")

    valid_ids = {
        c.id
        for c in (
            await db.execute(
                select(Category).where(
                    Category.id.in_(payload.category_ids), Category.is_active.is_(True)
                )
            )
        ).scalars().all()
    }
    if valid_ids != set(payload.category_ids):
        raise HTTPException(status_code=400, detail="One or more categories are invalid")

    for jt in payload.job_types:
        if jt not in JOB_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid job type: {jt}")

    for link in list(user.category_links):
        await db.delete(link)
    await db.flush()
    for cat_id in payload.category_ids:
        db.add(UserCategory(user_id=user.id, category_id=cat_id))

    user.job_types = payload.job_types
    user.status = "active"
    await db.flush()
    await db.refresh(user, attribute_names=["category_links"])

    is_first_completion = user.trial_ends_at is None
    await start_trial(db, user)

    if is_first_completion:
        await send_push_to_admins(
            db, "New student signed up (app)", user.full_name or "A student", {"type": "new_user"}
        )

    return MeOut(user=to_out(user), next_step=next_step(user))


@router.put("/push-token")
async def set_push_token(
    payload: PushTokenIn, user: User = Depends(current_student), db: AsyncSession = Depends(get_db)
) -> dict:
    user.expo_push_token = payload.token or None
    await db.flush()
    return {"ok": True}
