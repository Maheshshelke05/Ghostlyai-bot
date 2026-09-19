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
    district: Optional[str] = None
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
    next_step: str  # name | district | profile | done


class AuthOut(MeOut):
    access_token: str
    token_type: str = "bearer"
    is_new_user: bool
    suggested_category_slugs: list[str] = []


class PushTokenIn(BaseModel):
    token: Optional[str] = Field(default=None, max_length=200)


# ---------------------------------------------------------------------------
# Onboarding
# ---------------------------------------------------------------------------
class NameIn(BaseModel):
    full_name: str = Field(min_length=1, max_length=80)


class DistrictIn(BaseModel):
    district: str = Field(min_length=1, max_length=60)


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
class SupportMessageIn(BaseModel):
    text: str = Field(min_length=5, max_length=1000)


class SupportMessageOut(BaseModel):
    id: int
    direction: str  # in | out
    text: str
    created_at: str


class SupportThreadOut(BaseModel):
    messages: list[SupportMessageOut]
