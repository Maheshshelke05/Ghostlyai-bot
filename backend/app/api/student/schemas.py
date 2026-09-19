"""Pydantic request/response models for the student app API."""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
class StudentOut(BaseModel):
    id: int
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    language: str
    job_types: list[str] = []
    status: str
    category_ids: list[int] = []
    has_access: bool = False
    in_trial: bool = False
    access_until: Optional[str] = None

    model_config = {"from_attributes": True}


class MeOut(BaseModel):
    user: StudentOut
    next_step: str  # name | profile | done


class AuthOut(MeOut):
    access_token: str
    token_type: str = "bearer"
    is_new_user: bool
    suggested_category_slugs: list[str] = []


class SignupOut(BaseModel):
    """Response from POST /student/auth/resume. Never carries a full access_token - that's
    only issued by POST /student/auth/login, once a password exists and is verified."""
    is_new_user: bool
    needs_login: bool  # account already has a password - app should show Login, not set-password
    signup_token: Optional[str] = None  # present only when needs_login is False
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    suggested_category_slugs: list[str] = []


class SetPasswordIn(BaseModel):
    password: str = Field(min_length=8, max_length=72)  # 72 bytes is bcrypt's own hard limit
    # Only used (and only required) when the resume had neither a phone nor an email - without
    # at least one of those, there would be nothing to log in with afterward.
    phone: Optional[str] = Field(default=None, min_length=10, max_length=20)


class SetPasswordOut(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None


class LoginIn(BaseModel):
    identifier: str = Field(min_length=3, max_length=160)  # phone or email
    password: str = Field(min_length=1, max_length=72)


class PushTokenIn(BaseModel):
    token: Optional[str] = Field(default=None, max_length=200)


# ---------------------------------------------------------------------------
# Onboarding
# ---------------------------------------------------------------------------
class NameIn(BaseModel):
    full_name: str = Field(min_length=1, max_length=80)


class PhoneIn(BaseModel):
    phone: str = Field(min_length=10, max_length=20)


class ResumeSummaryOut(BaseModel):
    education: Optional[str] = None
    course: Optional[str] = None
    skills: list[str] = []
    experience_years: float = 0
    summary: Optional[str] = None
    suggested_category_slugs: list[str] = []


class CompleteOnboardingIn(BaseModel):
    category_ids: list[int] = Field(min_length=1, max_length=10)
    job_types: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Meta (public reference data)
# ---------------------------------------------------------------------------
class CategoryOut(BaseModel):
    id: int
    slug: str
    name: str


class SettingsOut(BaseModel):
    price_inr: int
    subscription_days: int
    trial_days: int
    max_categories: int


# ---------------------------------------------------------------------------
# Jobs (browsable feed)
# ---------------------------------------------------------------------------
class JobOut(BaseModel):
    id: int
    title: str
    company: str
    category_id: int
    qualification: Optional[str] = None
    district: Optional[str] = None
    location_text: Optional[str] = None
    job_type: str
    salary: Optional[str] = None
    description: Optional[str] = None
    last_date: Optional[date] = None
    created_at: str
    apply_url: str
    clicked: bool = False


class JobListOut(BaseModel):
    items: list[JobOut]
    next_cursor: Optional[str] = None


# ---------------------------------------------------------------------------
# Payments (native Razorpay Checkout SDK)
# ---------------------------------------------------------------------------
class CreateOrderOut(BaseModel):
    order_id: str
    amount: int  # paise
    currency: str = "INR"
    key_id: str


class VerifyPaymentIn(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class PaymentVerifiedOut(BaseModel):
    access_until: Optional[str] = None


# ---------------------------------------------------------------------------
# Support
# ---------------------------------------------------------------------------
class SupportMessageOut(BaseModel):
    id: int
    direction: str  # in | out
    subject: Optional[str] = None
    text: str
    image_url: Optional[str] = None
    created_at: str


class SupportThreadOut(BaseModel):
    messages: list[SupportMessageOut]
