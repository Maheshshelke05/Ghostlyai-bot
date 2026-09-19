"""Shared resume validation/parsing/storage logic for the student app - used both by the
resume-first signup endpoint (app/api/student/auth.py, no account yet) and the authenticated
re-upload endpoint (app/api/student/onboarding.py, updating an existing profile).
"""
from __future__ import annotations

from fastapi import HTTPException, UploadFile

from app.config import settings
from app.db.models import Profile, User
from app.services import ai, storage
from app.services.districts import canonical_district

_RESUME_MIME_BY_EXT = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}
SUPPORTED_RESUME_MIMES = set(_RESUME_MIME_BY_EXT.values())


async def read_and_validate_resume(file: UploadFile) -> tuple[bytes, str, str]:
    """Returns (data, resolved_mime, filename), or raises HTTPException on a bad file."""
    filename = file.filename or ""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    mime = file.content_type or ""
    resolved_mime = mime if mime in SUPPORTED_RESUME_MIMES else _RESUME_MIME_BY_EXT.get(ext)
    if resolved_mime is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Use PDF, DOCX or a photo (max {settings.MAX_RESUME_MB}MB).",
        )

    data = await file.read()
    max_bytes = settings.MAX_RESUME_MB * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(status_code=400, detail=f"File too large. Max {settings.MAX_RESUME_MB}MB.")
    return data, resolved_mime, filename


async def parse_resume_for_signup(db, data: bytes, mime: str):
    """Runs Gemini parsing only - raises HTTPException if the file isn't a readable resume."""
    from sqlalchemy import select

    from app.db.models import Category

    rows = (
        await db.execute(
            select(Category).where(Category.is_active.is_(True)).order_by(Category.sort_order)
        )
    ).scalars().all()
    categories = {c.slug: c.name for c in rows}

    result = await ai.parse_resume(data, mime, categories)
    if result is None:
        raise HTTPException(status_code=422, detail="Could not read this file. Try a clearer PDF or photo.")
    if not result.is_resume:
        raise HTTPException(status_code=422, detail="This doesn't look like a resume.")
    return result


async def apply_resume_to_user(db, user: User, data: bytes, mime: str, filename: str, result) -> Profile:
    """Saves the file and writes every extracted field onto the user's profile (and
    district/email opportunistically onto the user itself, same as the Telegram bot's
    on_resume_file)."""
    profile = user.profile
    path = await storage.save_resume(
        user.id, data, mime, filename,
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
    profile.resume_mime = mime
    profile.parsed_json = result.model_dump()
    await db.flush()

    if not user.district and result.city_or_district:
        canon = canonical_district(result.city_or_district)
        user.district = canon if canon else result.city_or_district.title()
    if not user.email and result.email:
        # Always lowercase - POST /student/auth/login matches on it case-sensitively, and
        # Gemini extracts the email exactly as it appears in the resume (any casing).
        user.email = result.email.strip().lower()[:160]
    await db.flush()

    return profile
