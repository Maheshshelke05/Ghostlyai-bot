"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-16

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("username", sa.String(64)),
        sa.Column("full_name", sa.String(120)),
        sa.Column("phone", sa.String(20)),
        sa.Column("district", sa.String(60)),
        sa.Column("language", sa.String(5), nullable=False, server_default="mr"),
        sa.Column("job_types", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(20), nullable=False, server_default="onboarding"),
        sa.Column("trial_ends_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("last_digest_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("last_teaser_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("reminder_sent_for", sa.String(40)),
        sa.Column("referred_by", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_users_status", "users", ["status"])
    op.create_index("ix_users_phone", "users", ["phone"])
    op.create_index("ix_users_district", "users", ["district"])
    op.create_index("ix_users_created", "users", ["created_at"])

    op.create_table(
        "profiles",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("education", sa.String(160)),
        sa.Column("course", sa.String(160)),
        sa.Column("skills", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("experience_years", sa.Numeric(4, 1), nullable=False, server_default="0"),
        sa.Column("summary", sa.Text()),
        sa.Column("resume_path", sa.String(255)),
        sa.Column("resume_mime", sa.String(80)),
        sa.Column("parsed_json", postgresql.JSONB()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(60), nullable=False, unique=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("name_mr", sa.String(80)),
        sa.Column("name_hi", sa.String(80)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"),
    )

    op.create_table(
        "user_categories",
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_index("ix_user_categories_category", "user_categories", ["category_id"])

    op.create_table(
        "admins",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("email", sa.String(120), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(128), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="owner"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "jobs",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=False),
        sa.Column("admin_id", sa.Integer(), sa.ForeignKey("admins.id", ondelete="SET NULL")),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("company", sa.String(160), nullable=False),
        sa.Column("qualification", sa.String(200)),
        sa.Column("district", sa.String(60)),
        sa.Column("location_text", sa.String(160)),
        sa.Column("job_type", sa.String(20), nullable=False, server_default="private"),
        sa.Column("salary", sa.String(80)),
        sa.Column("description", sa.Text()),
        sa.Column("apply_link", sa.String(500), nullable=False),
        sa.Column("last_date", sa.Date()),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("fingerprint", sa.String(64), nullable=False, unique=True),
        sa.Column("source", sa.String(80)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("job_type in ('govt','private','internship','wfh')", name="ck_jobs_job_type"),
        sa.CheckConstraint("status in ('active','expired','deleted')", name="ck_jobs_status"),
    )
    op.create_index("ix_jobs_match", "jobs", ["status", "category_id", "job_type", "created_at"])
    op.create_index("ix_jobs_district", "jobs", ["district"])
    op.create_index("ix_jobs_last_date", "jobs", ["last_date"])

    op.create_table(
        "job_deliveries",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("job_id", sa.BigInteger(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sent_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("clicked_at", sa.TIMESTAMP(timezone=True)),
        sa.UniqueConstraint("job_id", "user_id", name="uq_delivery_job_user"),
    )
    op.create_index("ix_deliveries_user", "job_deliveries", ["user_id"])
    op.create_index("ix_deliveries_sent_at", "job_deliveries", ["sent_at"])

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("start_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("end_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("source", sa.String(20), nullable=False, server_default="payment"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_subscriptions_user_end", "subscriptions", ["user_id", "end_at"])

    op.create_table(
        "payments",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("subscription_id", sa.BigInteger(), sa.ForeignKey("subscriptions.id", ondelete="SET NULL")),
        sa.Column("reference_id", sa.String(40), nullable=False, unique=True),
        sa.Column("razorpay_link_id", sa.String(40), unique=True),
        sa.Column("razorpay_payment_id", sa.String(40)),
        sa.Column("short_url", sa.String(255)),
        sa.Column("amount_paise", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="created"),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("paid_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_payments_status_paid", "payments", ["status", "paid_at"])

    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(60), primary_key=True),
        sa.Column("value", postgresql.JSONB()),
    )

    op.create_table(
        "broadcasts",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("admin_id", sa.Integer(), sa.ForeignKey("admins.id", ondelete="SET NULL")),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("audience", sa.String(20), nullable=False),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id")),
        sa.Column("total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("broadcasts")
    op.drop_table("app_settings")
    op.drop_table("payments")
    op.drop_table("subscriptions")
    op.drop_table("job_deliveries")
    op.drop_table("jobs")
    op.drop_table("admins")
    op.drop_table("user_categories")
    op.drop_table("categories")
    op.drop_table("profiles")
    op.drop_table("users")
