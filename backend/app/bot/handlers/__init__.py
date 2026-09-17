"""Root router: account commands first, then onboarding FSM, then fallback last."""
from __future__ import annotations

from aiogram import Router

from app.bot.handlers.account import router as account_router
from app.bot.handlers.support import router as support_router
from app.bot.handlers.onboarding import router as onboarding_router
from app.bot.handlers.fallback import router as fallback_router

root_router = Router(name="root")
root_router.include_router(account_router)
root_router.include_router(support_router)
root_router.include_router(onboarding_router)
root_router.include_router(fallback_router)
