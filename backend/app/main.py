"""FastAPI application entrypoint: lifespan, health check, routers."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.db.session import engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("app")


async def _check_db() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001
        logger.exception("DB health check failed")
        return False


async def _check_redis() -> bool:
    if not settings.REDIS_URL:
        return True  # Redis is optional in local dev (falls back to in-memory FSM storage)
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(settings.REDIS_URL)
        try:
            await client.ping()
        finally:
            await client.aclose()
        return True
    except Exception:  # noqa: BLE001
        logger.exception("Redis health check failed")
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Student Job Alert Bot API (env=%s)", settings.APP_ENV)

    if settings.is_production and settings.BOT_TOKEN:
        try:
            from app.bot.loader import get_bot

            bot = get_bot()
            webhook_url = f"{settings.BASE_URL.rstrip('/')}/webhooks/telegram"
            await bot.set_webhook(
                url=webhook_url,
                secret_token=settings.TELEGRAM_WEBHOOK_SECRET or None,
                drop_pending_updates=False,
            )
            logger.info("Telegram webhook set to %s", webhook_url)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to set Telegram webhook")

    yield

    logger.info("Shutting down API")
    try:
        from app.bot.loader import get_bot

        await get_bot().session.close()
    except Exception:  # noqa: BLE001
        pass
    await engine.dispose()


app = FastAPI(title="Student Job Alert Bot API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    db_ok = await _check_db()
    redis_ok = await _check_redis()
    return {"db": "ok" if db_ok else "error", "redis": "ok" if redis_ok else "error"}


# ---------------------------------------------------------------------------
# Routers (added incrementally as each module is implemented)
# ---------------------------------------------------------------------------
from app.api.webhooks.telegram import router as telegram_webhook_router  # noqa: E402
from app.api.webhooks.razorpay import router as razorpay_webhook_router  # noqa: E402
from app.api.redirect import router as redirect_router  # noqa: E402
from app.api.admin.auth import router as admin_auth_router  # noqa: E402
from app.api.admin.dashboard import router as admin_dashboard_router  # noqa: E402
from app.api.admin.meta import router as admin_meta_router  # noqa: E402
from app.api.admin.jobs import router as admin_jobs_router  # noqa: E402
from app.api.admin.users import router as admin_users_router  # noqa: E402
from app.api.admin.categories import router as admin_categories_router  # noqa: E402
from app.api.admin.payments import router as admin_payments_router  # noqa: E402
from app.api.admin.settings import router as admin_settings_router  # noqa: E402
from app.api.admin.broadcast import router as admin_broadcast_router  # noqa: E402
from app.api.admin.staff import router as admin_staff_router  # noqa: E402

app.include_router(telegram_webhook_router)
app.include_router(razorpay_webhook_router)
app.include_router(redirect_router)
app.include_router(admin_auth_router)
app.include_router(admin_dashboard_router)
app.include_router(admin_meta_router)
app.include_router(admin_jobs_router)
app.include_router(admin_users_router)
app.include_router(admin_categories_router)
app.include_router(admin_payments_router)
app.include_router(admin_settings_router)
app.include_router(admin_broadcast_router)
app.include_router(admin_staff_router)
