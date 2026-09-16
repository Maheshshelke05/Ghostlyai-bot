"""Pydantic request/response models for the admin API (Chapter 17)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
class LoginIn(BaseModel):
    email: EmailStr
    password: str


class AdminOut(BaseModel):
    id: int
    name: str
    email: str
    role: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin: AdminOut


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------
class JobIn(BaseModel):
    title: str
    company: str
    category_slug: str
    qualification: Optional[str] = None
    district: Optional[str] = None
    location_text: Optional[str] = None
    job_type: str = "private"
    salary: Optional[str] = None
    apply_link: str
    last_date: Optional[str] = None  # YYYY-MM-DD / DD-MM-YYYY / DD/MM/YYYY
    description: Optional[str] = None


class JobOut(BaseModel):
    id: int
    title: str
    company: str
    category_id: int
    category_slug: Optional[str] = None
    qualification: Optional[str] = None
    district: Optional[str] = None
    location_text: Optional[str] = None
    job_type: str
    salary: Optional[str] = None
    apply_link: str
    last_date: Optional[date] = None
    status: str
    created_at: datetime
    sent_count: int = 0
    click_count: int = 0

    model_config = {"from_attributes": True}


class BatchJobsIn(BaseModel):
    jobs: list[JobIn] = Field(max_length=200)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
class ExtendIn(BaseModel):
    days: int = Field(gt=0, le=3650)
    notify: bool = True


class MessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------
class CategoryIn(BaseModel):
    slug: str
    name: str
    name_mr: Optional[str] = None
    name_hi: Optional[str] = None
    sort_order: int = 100


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    name_mr: Optional[str] = None
    name_hi: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
class SettingsIn(BaseModel):
    price_inr: Optional[int] = Field(default=None, gt=0)
    subscription_days: Optional[int] = Field(default=None, gt=0)
    trial_days: Optional[int] = Field(default=None, ge=0)
    digest_times: Optional[list[str]] = None
    digest_max_jobs: Optional[int] = Field(default=None, gt=0, le=50)
    max_categories: Optional[int] = Field(default=None, gt=0, le=10)
    teaser_every_hours: Optional[int] = Field(default=None, gt=0)

    @field_validator("digest_times")
    @classmethod
    def _validate_times(cls, value: Optional[list[str]]) -> Optional[list[str]]:
        if value is None:
            return value
        import re

        pattern = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
        for item in value:
            if not pattern.match(item):
                raise ValueError(f"invalid HH:MM time: {item!r}")
        return sorted(set(value))


# ---------------------------------------------------------------------------
# Broadcast
# ---------------------------------------------------------------------------
class BroadcastPreviewIn(BaseModel):
    audience: str
    category_id: Optional[int] = None


class BroadcastIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    audience: str
    category_id: Optional[int] = None


# ---------------------------------------------------------------------------
# Staff
# ---------------------------------------------------------------------------
class StaffIn(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=8)
    role: str = "uploader"


class StaffUpdate(BaseModel):
    is_active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=8)
