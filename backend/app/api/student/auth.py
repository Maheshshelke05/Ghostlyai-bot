"""POST /student/auth/phone, GET /student/auth/me - phone-based login for the student app.

If the verified phone already belongs to an existing Telegram-bot user, that account is reused
as-is (their Telegram-verified phone is trusted, no extra OTP) - otherwise a new app-only User
row is created (telegram_id=None) and the normal onboarding steps follow.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.student.deps import STUDENT_ROLE, current_student
from app.api.student.schemas import AuthOut, MeOut, PhoneAuthIn, StudentOut
from app.db.models import User
from app.db.session import get_db
from app.services import ratelimit
from app.services.access import access_until, has_access, in_trial
from app.services.auth import create_token
from app.services.firebase_auth import FirebaseAuthError, verify_phone_token
from app.services.validators import normalize_phone

router = APIRouter(prefix="/student/auth", tags=["student-auth"])

# A consumer app shouldn't force a phone-OTP re-login every few days like the admin app does -
# there is no refresh-token flow here, so the token itself just lives longer.
_STUDENT_TOKEN_HOURS = 24 * 30


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def next_step(user: User) -> str:
    """Mirrors the completeness check in bot/handlers/onboarding.py::cmd_start, plus the
    app-only steps (name, district) that come before the shared resume/categories/job-types
    flow, which the app completes in one local session ending in POST /student/me/complete."""
    if user.status == "active" and user.category_links:
        return "done"
    if not user.full_name:
        return "name"
    if not user.district:
        return "district"
    return "profile"


def to_out(user: User) -> StudentOut:
    until = access_until(user)
    return StudentOut(
        id=user.id,
        full_name=user.full_name,
        phone=user.phone,
        district=user.district,
        language=user.language,
        job_types=user.job_types,
        status=user.status,
        category_ids=user.category_ids,
        has_access=has_access(user),
        in_trial=in_trial(user),
        access_until=until.isoformat() if until else None,
    )


@router.post("/phone", response_model=AuthOut)
async def login_with_phone(
    payload: PhoneAuthIn, request: Request, db: AsyncSession = Depends(get_db)
) -> AuthOut:
    limit_key = f"{_client_ip(request)}|phone-auth"
    wait = ratelimit.seconds_until_allowed(limit_key)
    if wait:
        raise HTTPException(
            status_code=429,
            detail="Too many attempts. Try again in a few minutes.",
            headers={"Retry-After": str(wait)},
        )

    try:
        phone = normalize_phone(await verify_phone_token(payload.id_token))
    except FirebaseAuthError as exc:
        ratelimit.record_failure(limit_key)
        raise HTTPException(status_code=401, detail=str(exc))

    ratelimit.clear(limit_key)

    user = (await db.execute(select(User).where(User.phone == phone))).scalar_one_or_none()
    is_new_user = user is None
    if user is None:
        user = User(phone=phone, telegram_id=None, status="onboarding", language="mr")
        db.add(user)
        await db.flush()
        await db.refresh(user, attribute_names=["category_links", "subscriptions"])
    elif user.status == "blocked":
        raise HTTPException(status_code=403, detail="This account has been blocked")

    token = create_token(user.id, STUDENT_ROLE, expire_hours=_STUDENT_TOKEN_HOURS)
    return AuthOut(
        access_token=token,
        is_new_user=is_new_user,
        next_step=next_step(user),
        user=to_out(user),
    )


@router.get("/me", response_model=MeOut)
async def me(user: User = Depends(current_student)) -> MeOut:
    return MeOut(user=to_out(user), next_step=next_step(user))
