"""Onboarding endpoints for the student app: name -> complete (categories + job types). The app
does not collect district at all (unlike the Telegram bot) - matching never used it (see
CLAUDE.md BUSINESS RULES). Resume upload itself happens at signup
(app/api/student/auth.py::signup_with_resume); this router keeps the authenticated re-upload
endpoint for updating it later.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.student.auth import next_step, to_out
from app.api.student.deps import current_student
from app.api.student.schemas import (
    CompleteOnboardingIn,
    MeOut,
    NameIn,
    PhoneIn,
    PushTokenIn,
    ResumeSummaryOut,
)
from app.db.models import Category, User, UserCategory
from app.db.session import get_db
from app.services.access import get_setting, start_trial
from app.services.jobs import JOB_TYPES
from app.services.push import send_push_to_admins
from app.services.resume_intake import (
    apply_resume_to_user,
    parse_resume_for_signup,
    read_and_validate_resume,
)
from app.services.validators import normalize_name, normalize_phone, valid_name

router = APIRouter(prefix="/student/me", tags=["student-onboarding"])


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


@router.put("/phone", response_model=MeOut)
async def set_phone(
    payload: PhoneIn, user: User = Depends(current_student), db: AsyncSession = Depends(get_db)
) -> MeOut:
    """Manual fallback when the resume had no phone number (or the wrong one) - trusted as
    typed, same as everything else about this signup flow; not re-verified."""
    phone = normalize_phone(payload.phone)
    existing = (
        await db.execute(select(User).where(User.phone == phone, User.id != user.id))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=400, detail="This number is already registered")
    user.phone = phone
    await db.flush()
    return MeOut(user=to_out(user), next_step=next_step(user))


@router.post("/resume", response_model=ResumeSummaryOut)
async def upload_resume(
    file: UploadFile = File(...),
    user: User = Depends(current_student),
    db: AsyncSession = Depends(get_db),
) -> ResumeSummaryOut:
    """Re-upload/update the resume after signup (signup itself already captured one)."""
    data, resolved_mime, filename = await read_and_validate_resume(file)
    result = await parse_resume_for_signup(db, data, resolved_mime)
    profile = await apply_resume_to_user(db, user, data, resolved_mime, filename, result)

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
