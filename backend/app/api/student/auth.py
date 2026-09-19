"""POST /student/auth/resume, GET /student/auth/me - resume-first signup for the student app.

No phone verification: the student uploads a resume, Gemini extracts name/phone/email/
education from it, and that's trusted as-is (same trust model the Telegram bot already has for
whatever a user types - this app just gets its identity fields from a document instead of a
chat). If the extracted phone already belongs to an existing Telegram-bot user, that account is
reused as-is (their existing profile is trusted) - otherwise a new app-only User row is created
(telegram_id=None) and the normal onboarding steps follow.

The app collects the student's name itself (a screen before the resume upload) rather than
relying only on what Gemini extracts, since a self-typed name is more reliable and lets the app
show it immediately without waiting on parsing - `full_name` here is that user-typed value and
takes priority over the resume's own extraction (but never overwrites an existing, already-named
account recognized by phone).
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.student.deps import STUDENT_ROLE, current_student
from app.api.student.schemas import AuthOut, MeOut, StudentOut
from app.db.models import User, utcnow
from app.db.session import get_db
from app.services import ratelimit
from app.services.access import access_until, has_access, in_trial
from app.services.auth import create_token
from app.services.resume_intake import (
    apply_resume_to_user,
    parse_resume_for_signup,
    read_and_validate_resume,
)
from app.services.validators import normalize_name, normalize_phone, valid_name

router = APIRouter(prefix="/student/auth", tags=["student-auth"])

# A consumer app shouldn't force a re-login every few days like the admin app does - there is
# no refresh-token flow here, so the token itself just lives longer.
_STUDENT_TOKEN_HOURS = 24 * 30


def next_step(user: User) -> str:
    """Mirrors the completeness check in bot/handlers/onboarding.py::cmd_start, plus the
    app-only name step that comes before the shared categories/job-types flow (the app does
    not collect district at all), which the app completes in one local session ending in
    POST /student/me/complete."""
    if user.status == "active" and user.category_links:
        return "done"
    if not user.full_name:
        return "name"
    return "profile"


def to_out(user: User) -> StudentOut:
    until = access_until(user)
    return StudentOut(
        id=user.id,
        full_name=user.full_name,
        phone=user.phone,
        email=user.email,
        language=user.language,
        job_types=user.job_types,
        status=user.status,
        category_ids=user.category_ids,
        has_access=has_access(user),
        in_trial=in_trial(user),
        access_until=until.isoformat() if until else None,
    )


@router.post("/resume", response_model=AuthOut)
async def signup_with_resume(
    request: Request,
    file: UploadFile = File(...),
    full_name: Optional[str] = Form(default=None, max_length=80),
    db: AsyncSession = Depends(get_db),
) -> AuthOut:
    # Unauthenticated by design (this IS signup) and every attempt costs a real Gemini call
    # regardless of outcome, so cap attempts per IP - otherwise anyone can spam this for free
    # to run up the Gemini bill and fill the DB with junk users.
    limit_key = f"resume|{ratelimit.client_ip(request)}"
    wait = ratelimit.seconds_until_allowed(limit_key)
    if wait:
        raise HTTPException(
            status_code=429,
            detail="Too many resume uploads from this network. Try again in a few minutes.",
            headers={"Retry-After": str(wait)},
        )
    ratelimit.record_attempt(limit_key)

    data, resolved_mime, filename = await read_and_validate_resume(file)
    result = await parse_resume_for_signup(db, data, resolved_mime)

    phone = normalize_phone(result.phone) if result.phone else None
    user = None
    if phone:
        user = (await db.execute(select(User).where(User.phone == phone))).scalar_one_or_none()

    chosen_name = None
    if full_name and valid_name(full_name.strip()):
        chosen_name = normalize_name(full_name.strip())
    elif result.full_name and valid_name(result.full_name):
        chosen_name = normalize_name(result.full_name)

    is_new_user = user is None
    if user is None:
        user = User(phone=phone, telegram_id=None, full_name=chosen_name, status="onboarding", language="mr")
        db.add(user)
        await db.flush()
        await db.refresh(user, attribute_names=["category_links", "subscriptions", "profile"])
    elif user.status == "blocked":
        raise HTTPException(status_code=403, detail="This account has been blocked")
    elif not user.full_name and chosen_name:
        user.full_name = chosen_name

    if user.app_seen_at is None:
        user.app_seen_at = utcnow()

    await apply_resume_to_user(db, user, data, resolved_mime, filename, result)

    token = create_token(user.id, STUDENT_ROLE, expire_hours=_STUDENT_TOKEN_HOURS)
    return AuthOut(
        access_token=token,
        is_new_user=is_new_user,
        next_step=next_step(user),
        user=to_out(user),
        suggested_category_slugs=result.suggested_category_slugs,
    )


@router.get("/me", response_model=MeOut)
async def me(user: User = Depends(current_student)) -> MeOut:
    return MeOut(user=to_out(user), next_step=next_step(user))
