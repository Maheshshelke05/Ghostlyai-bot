"""Central application settings, loaded from environment variables (.env)."""
from __future__ import annotations

import os
from functools import lru_cache
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ---------- App ----------
    APP_ENV: str = "development"  # development | production
    # Render web services get RENDER_EXTERNAL_URL injected automatically; used as a fallback
    # so BASE_URL doesn't have to be hardcoded for the web service (the worker, which has no
    # public URL of its own, still needs BASE_URL set explicitly - see render.yaml).
    BASE_URL: str = os.environ.get("RENDER_EXTERNAL_URL") or "http://localhost:8000"
    TIMEZONE: str = "Asia/Kolkata"
    CORS_ORIGINS: str = "*"

    # ---------- Database ----------
    DATABASE_URL: str = "postgresql+asyncpg://jobbot:jobbot@localhost:5432/jobbot"
    REDIS_URL: str = ""

    # ---------- Telegram ----------
    BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = ""
    SUPPORT_USERNAME: str = ""
    ADMIN_ALERT_CHAT_ID: str = ""

    # ---------- Gemini ----------
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.8-flash"

    # ---------- Razorpay ----------
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""

    # ---------- Admin auth ----------
    JWT_SECRET: str = "dev-secret-change-me"
    JWT_EXPIRE_HOURS: int = 72

    # ---------- Files ----------
    UPLOAD_DIR: str = "./data/resumes"
    MAX_RESUME_MB: int = 10

    # ---------- Cloudinary (resume storage; optional, falls back to local disk) ----------
    CLOUDINARY_URL: str = ""

    # ---------- Firebase (student app phone-auth ID token verification) ----------
    # Raw JSON of a Firebase service account key (Project Settings -> Service accounts ->
    # Generate new private key), as a single-line string - same single-env-var style as
    # CLOUDINARY_URL above.
    FIREBASE_SERVICE_ACCOUNT_JSON: str = ""

    # ---------- Student app auth ----------
    STUDENT_JWT_EXPIRE_HOURS: int = 24 * 30

    # ---------- GhostlyAI.in admin API (sister product, surfaced in the admin app) ----------
    GHOSTLY_API_BASE_URL: str = ""
    GHOSTLY_API_KEY: str = ""
    # Their custom authorizer's header name isn't confirmed yet; change this once it is,
    # instead of editing code. "Authorization" is auto-prefixed with "Bearer " if used.
    GHOSTLY_API_AUTH_HEADER: str = "x-api-key"

    # ---------- Scheduler ----------
    # When true, the API process itself runs the APScheduler jobs (digest, reminders, expiry,
    # broadcasts) in-process instead of expecting a separate `app.workers.scheduler` process.
    # For a single free-tier web service with no paid background worker (Render's free plan has
    # no worker option at all) - NEVER combine with more than one uvicorn worker process
    # (`--workers N > 1`), each would run its own copy of every scheduled job and send every
    # digest N times.
    RUN_SCHEDULER_IN_API: bool = False

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.TIMEZONE)

    @property
    def cors_origins_list(self) -> list[str]:
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

if settings.CLOUDINARY_URL:
    # The cloudinary SDK's own env-based config loader parses this URL correctly (cloud
    # name/api key/secret) - but only if it's in the actual process environment, which
    # pydantic-settings does NOT do for values that came from a .env file. Setting it here,
    # as early as possible in the import chain, ensures it's present before `import
    # cloudinary` ever runs anywhere else in the app.
    os.environ.setdefault("CLOUDINARY_URL", settings.CLOUDINARY_URL)
