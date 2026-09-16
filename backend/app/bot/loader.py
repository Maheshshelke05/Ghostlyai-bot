"""Singleton Bot + Dispatcher, with Redis-backed FSM storage (falls back to memory)."""
from __future__ import annotations

from functools import lru_cache

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings

_STATE_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 days


@lru_cache
def get_bot() -> Bot:
    return Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


@lru_cache
def get_storage():
    if settings.REDIS_URL:
        from aiogram.fsm.storage.redis import RedisStorage

        return RedisStorage.from_url(
            settings.REDIS_URL,
            state_ttl=_STATE_TTL_SECONDS,
            data_ttl=_STATE_TTL_SECONDS,
        )
    return MemoryStorage()


@lru_cache
def get_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=get_storage())

    from app.bot.middlewares import DbUserMiddleware
    from app.bot.handlers import root_router

    dp.message.middleware(DbUserMiddleware())
    dp.callback_query.middleware(DbUserMiddleware())
    dp.include_router(root_router)
    return dp
