"""SQLAlchemy 2 typed models for the Student Job Alert Bot."""
from __future__ import annotations

import hashlib
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, TypeDecorator, TIMESTAMP


def utcnow() -> datetime:
    """Current time, timezone-aware, in UTC."""
    return datetime.now(timezone.utc)


def as_utc(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware UTC (assumes naive datetimes are already UTC)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class JSONBType(TypeDecorator):
    """JSONB on Postgres, plain JSON elsewhere (e.g. SQLite in tests)."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


class TZDateTime(TypeDecorator):
    """Always-aware UTC datetime, portable across Postgres and SQLite."""

    impl = TIMESTAMP(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return as_utc(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return as_utc(value)


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# users
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(64))
    full_name: Mapped[Optional[str]] = mapped_column(String(120))
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    district: Mapped[Optional[str]] = mapped_column(String(60))
    language: Mapped[str] = mapped_column(String(5), nullable=False, default="mr")
    job_types: Mapped[list] = mapped_column(JSONBType, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="onboarding")
    # onboarding | active | blocked | bot_blocked

    trial_ends_at: Mapped[Optional[datetime]] = mapped_column(TZDateTime)
    last_digest_at: Mapped[Optional[datetime]] = mapped_column(TZDateTime)
    last_teaser_at: Mapped[Optional[datetime]] = mapped_column(TZDateTime)
    reminder_sent_for: Mapped[Optional[str]] = mapped_column(String(40))
    referred_by: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL")
    )

    created_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        TZDateTime, nullable=False, default=utcnow, onupdate=utcnow
    )

    profile: Mapped[Optional["Profile"]] = relationship(
        back_populates="user", uselist=False, lazy="selectin", cascade="all, delete-orphan"
    )
    category_links: Mapped[list["UserCategory"]] = relationship(
        back_populates="user", lazy="selectin", cascade="all, delete-orphan"
    )
    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="user", lazy="selectin", cascade="all, delete-orphan",
        order_by="Subscription.end_at.desc()",
    )
    payments: Mapped[list["Payment"]] = relationship(back_populates="user", lazy="selectin")

    @property
    def category_ids(self) -> list[int]:
        return [link.category_id for link in self.category_links]

    __table_args__ = (
        Index("ix_users_status", "status"),
        Index("ix_users_phone", "phone"),
        Index("ix_users_district", "district"),
        Index("ix_users_created", "created_at"),
    )


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    education: Mapped[Optional[str]] = mapped_column(String(160))
    course: Mapped[Optional[str]] = mapped_column(String(160))
    skills: Mapped[list] = mapped_column(JSONBType, nullable=False, default=list)
    experience_years: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False, default=0)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    resume_path: Mapped[Optional[str]] = mapped_column(String(255))
    resume_mime: Mapped[Optional[str]] = mapped_column(String(80))
    parsed_json: Mapped[Optional[dict]] = mapped_column(JSONBType)
    updated_at: Mapped[datetime] = mapped_column(
        TZDateTime, nullable=False, default=utcnow, onupdate=utcnow
    )

    user: Mapped["User"] = relationship(back_populates="profile")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    name_mr: Mapped[Optional[str]] = mapped_column(String(80))
    name_hi: Mapped[Optional[str]] = mapped_column(String(80))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100)

    def label(self, lang: str) -> str:
        if lang == "mr" and self.name_mr:
            return self.name_mr
        if lang == "hi" and self.name_hi:
            return self.name_hi
        return self.name


class UserCategory(Base):
    __tablename__ = "user_categories"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True
    )

    user: Mapped["User"] = relationship(back_populates="category_links")
    category: Mapped["Category"] = relationship(lazy="selectin")

    __table_args__ = (Index("ix_user_categories_category", "category_id"),)


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="owner")  # owner|uploader
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False, default=utcnow)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id"), nullable=False)
    admin_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("admins.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    company: Mapped[str] = mapped_column(String(160), nullable=False)
    qualification: Mapped[Optional[str]] = mapped_column(String(200))
    district: Mapped[Optional[str]] = mapped_column(String(60))  # NULL = anywhere
    location_text: Mapped[Optional[str]] = mapped_column(String(160))
    job_type: Mapped[str] = mapped_column(String(20), nullable=False, default="private")
    salary: Mapped[Optional[str]] = mapped_column(String(80))
    description: Mapped[Optional[str]] = mapped_column(Text)
    apply_link: Mapped[str] = mapped_column(String(500), nullable=False)
    last_date: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    # active | expired | deleted
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False, default=utcnow)

    category: Mapped["Category"] = relationship(lazy="selectin")

    __table_args__ = (
        Index("ix_jobs_match", "status", "category_id", "job_type", "created_at"),
        Index("ix_jobs_district", "district"),
        Index("ix_jobs_last_date", "last_date"),
        CheckConstraint(
            "job_type in ('govt','private','internship','wfh')", name="ck_jobs_job_type"
        ),
        CheckConstraint("status in ('active','expired','deleted')", name="ck_jobs_status"),
    )

    @staticmethod
    def make_fingerprint(title: str, company: str, apply_link: str) -> str:
        normalized = "|".join(
            " ".join(part.lower().split()) for part in (title, company, apply_link)
        )
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class JobDelivery(Base):
    __tablename__ = "job_deliveries"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    job_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("jobs.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    sent_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False, default=utcnow)
    clicked_at: Mapped[Optional[datetime]] = mapped_column(TZDateTime)

    job: Mapped["Job"] = relationship(lazy="selectin")

    __table_args__ = (
        UniqueConstraint("job_id", "user_id", name="uq_delivery_job_user"),
        Index("ix_deliveries_user", "user_id"),
        Index("ix_deliveries_sent_at", "sent_at"),
    )


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    start_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)
    end_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="payment")
    created_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False, default=utcnow)

    user: Mapped["User"] = relationship(back_populates="subscriptions")

    __table_args__ = (Index("ix_subscriptions_user_end", "user_id", "end_at"),)


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL")
    )
    subscription_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("subscriptions.id", ondelete="SET NULL")
    )
    reference_id: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    razorpay_link_id: Mapped[Optional[str]] = mapped_column(String(40), unique=True)
    razorpay_payment_id: Mapped[Optional[str]] = mapped_column(String(40))
    short_url: Mapped[Optional[str]] = mapped_column(String(255))
    amount_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="created")
    # created | paid | expired
    expires_at: Mapped[Optional[datetime]] = mapped_column(TZDateTime)
    paid_at: Mapped[Optional[datetime]] = mapped_column(TZDateTime)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False, default=utcnow)

    user: Mapped[Optional["User"]] = relationship(back_populates="payments")

    __table_args__ = (Index("ix_payments_status_paid", "status", "paid_at"),)


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSONBType)


class Broadcast(Base):
    __tablename__ = "broadcasts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    admin_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("admins.id", ondelete="SET NULL")
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    audience: Mapped[str] = mapped_column(String(20), nullable=False)
    category_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("categories.id"))
    total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    # queued | running | done
    created_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False, default=utcnow)
