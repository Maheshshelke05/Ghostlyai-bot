"""Tiny Redis-backed cache for expensive, read-heavy admin endpoints (dashboard, delivery
stats). Falls back to "no cache, just compute" if REDIS_URL isn't set - Redis is already
optional everywhere else in this app (the bot's FSM storage falls back to in-memory), so this
matches that convention rather than making Redis a hard requirement.

These endpoints are aggregate counts an admin is glancing at, not data they're editing - a few
seconds of staleness is a fine trade for turning a several-second page load into an instant one
on every repeat view within the TTL (auto-refresh intervals, pull-to-refresh, re-opening a tab).
"""
from __future__ import annotations

import json
import logging
from typing import Any, Awaitable, Callable

from app.config import settings

logger = logging.getLogger("app.cache")

_client: Any = None
_client_checked = False


def _get_client() -> Any:
    global _client, _client_checked
    if not settings.REDIS_URL:
        return None
    if not _client_checked:
        _client_checked = True
        try:
            import redis.asyncio as aioredis

            _client = aioredis.from_url(settings.REDIS_URL)
        except Exception:  # noqa: BLE001
            logger.exception("Could not create Redis client for caching")
            _client = None
    return _client


async def get_or_set(key: str, ttl_seconds: int, compute: Callable[[], Awaitable[Any]]) -> Any:
    """Returns the cached JSON value for `key` if present, otherwise calls `compute()`, caches
    the result for `ttl_seconds`, and returns it. Any Redis failure just falls through to
    calling `compute()` directly - a cache outage should never break the endpoint."""
    client = _get_client()
    if client is None:
        return await compute()

    try:
        cached = await client.get(key)
        if cached is not None:
            return json.loads(cached)
    except Exception:  # noqa: BLE001
        logger.warning("Cache read failed for %s", key, exc_info=True)

    value = await compute()

    try:
        await client.set(key, json.dumps(value), ex=ttl_seconds)
    except Exception:  # noqa: BLE001
        logger.warning("Cache write failed for %s", key, exc_info=True)

    return value


async def invalidate(*keys: str) -> None:
    client = _get_client()
    if client is None or not keys:
        return
    try:
        await client.delete(*keys)
    except Exception:  # noqa: BLE001
        logger.warning("Cache invalidate failed for %s", keys, exc_info=True)
