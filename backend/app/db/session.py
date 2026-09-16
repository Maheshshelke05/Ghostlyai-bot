"""Async SQLAlchemy engine/session setup."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings


def _prepare_asyncpg_url(raw_url: str) -> tuple[str, dict[str, Any]]:
    """Makes a Postgres URL safe for asyncpg regardless of where it came from.

    Managed providers (Neon, Supabase, ...) commonly hand out plain `postgresql://` URLs
    with libpq-only query params (`sslmode`, `channel_binding`) that asyncpg's connect()
    does not understand and will reject outright. This rewrites the scheme to
    `postgresql+asyncpg://`, strips those params, and translates `sslmode=require` (or
    stricter) into an explicit `ssl=True` connect arg instead. Local/plain URLs without
    those params pass through unchanged.
    """
    parts = urlsplit(raw_url)
    scheme = parts.scheme
    if scheme in ("postgres", "postgresql"):
        scheme = "postgresql+asyncpg"

    connect_args: dict[str, Any] = {}
    kept_params = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if key == "sslmode":
            if value.lower() in ("require", "verify-ca", "verify-full"):
                connect_args["ssl"] = True
            continue
        if key == "channel_binding":
            continue  # libpq-only; asyncpg has no equivalent
        kept_params.append((key, value))

    cleaned_url = urlunsplit((scheme, parts.netloc, parts.path, urlencode(kept_params), parts.fragment))
    return cleaned_url, connect_args


_database_url, _connect_args = _prepare_asyncpg_url(settings.DATABASE_URL)
engine = create_async_engine(
    _database_url, pool_pre_ping=True, future=True, connect_args=_connect_args
)

SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yields a session, commits on success, rolls back on error."""
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Context manager for use in the bot and workers (outside FastAPI's DI)."""
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
