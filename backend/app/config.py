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
