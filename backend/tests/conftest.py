"""Shared pytest fixtures: an isolated in-memory SQLite DB per test, seeded categories,
user factories in every access state, a FakeBot that records sent messages, and an httpx
ASGI test client wired to the real FastAPI app with the DB dependency overridden."""
from __future__ import annotations

from datetime import timedelta
from typing import Any, Optional

import pytest
import pytest_asyncio
from aiogram.methods import SendMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.models import Category, Job, Subscription, User, utcnow
from app.db.seed import seed_all


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    from app.db.models import Base

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db(engine):
    session_factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with session_factory() as session:
        await seed_all(session)
        yield session


@pytest_asyncio.fixture
async def categories(db) -> dict[str, Category]:
    rows = (await db.execute(select(Category))).scalars().all()
    return {c.slug: c for c in rows}


_next_telegram_id = 100_000


async def make_user(
    db,
    *,
    status: str = "active",
    district: Optional[str] = "Nagpur",
    job_types: Optional[list[str]] = None,
    category_slugs: Optional[list[str]] = None,
    trial_ends_at=None,
    paid_until=None,
    full_name: str = "Test User",
) -> User:
    global _next_telegram_id
    _next_telegram_id += 1

    user = User(
        telegram_id=_next_telegram_id,
        full_name=full_name,
        phone="+919876543210",
        district=district,
        language="mr",
        job_types=job_types or [],
        status=status,
        trial_ends_at=trial_ends_at,
    )
    db.add(user)
    await db.flush()

    if category_slugs:
        from app.db.models import UserCategory

        cats = (
            await db.execute(select(Category).where(Category.slug.in_(category_slugs)))
        ).scalars().all()
        for cat in cats:
            db.add(UserCategory(user_id=user.id, category_id=cat.id))
        await db.flush()

    if paid_until is not None:
        db.add(Subscription(user_id=user.id, start_at=utcnow() - timedelta(days=1), end_at=paid_until, source="payment"))
        await db.flush()

    await db.refresh(user, attribute_names=["category_links", "subscriptions"])
    return user


async def make_job(
    db,
    categories: dict[str, Category],
    *,
    category_slug: str = "accounts-finance",
    title: str = "Test Job",
    company: str = "Test Co",
    apply_link: Optional[str] = None,
    district: Optional[str] = "Nagpur",
    job_type: str = "private",
    last_date=None,
    created_at=None,
    status: str = "active",
) -> Job:
    from app.services.jobs import fingerprint

    n = id(object())
    link = apply_link or f"https://example.com/apply/{n}"
    job = Job(
        category_id=categories[category_slug].id,
        title=title,
        company=company,
        district=district,
        job_type=job_type,
        apply_link=link,
        last_date=last_date,
        status=status,
        fingerprint=fingerprint(title, company, link),
        created_at=created_at or utcnow(),
    )
    db.add(job)
    await db.flush()
    await db.refresh(job, attribute_names=["category"])
    return job


class FakeBot:
    """Records every send_message call; can be told to raise per-chat-id for specific tests."""

    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []
        self.forbidden_chat_ids: set[int] = set()
        self.retry_after_once: dict[int, int] = {}
        self.bad_request_chat_ids: set[int] = set()

    async def send_message(self, chat_id, text, reply_markup=None, disable_web_page_preview=None):
        if chat_id in self.retry_after_once:
            from aiogram.exceptions import TelegramRetryAfter

            seconds = self.retry_after_once.pop(chat_id)
            raise TelegramRetryAfter(
                method=SendMessage(chat_id=chat_id, text=text), message="Too Many Requests", retry_after=seconds
            )
        if chat_id in self.forbidden_chat_ids:
            from aiogram.exceptions import TelegramForbiddenError

            raise TelegramForbiddenError(
                method=SendMessage(chat_id=chat_id, text=text), message="Forbidden: bot was blocked by the user"
            )
        if chat_id in self.bad_request_chat_ids:
            from aiogram.exceptions import TelegramBadRequest

            raise TelegramBadRequest(method=SendMessage(chat_id=chat_id, text=text), message="Bad Request")

        self.sent.append({"chat_id": chat_id, "text": text, "reply_markup": reply_markup})
        return object()


@pytest.fixture
def fake_bot(monkeypatch):
    bot = FakeBot()
    return bot


@pytest_asyncio.fixture
async def client(engine, monkeypatch):
    """httpx AsyncClient wired to the real FastAPI app, DB dependency overridden to `engine`."""
    import httpx

    import app.main as main_module
    from app.db.session import get_db

    session_factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)

    async def _override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    main_module.app.dependency_overrides[get_db] = _override_get_db

    transport = httpx.ASGITransport(app=main_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    main_module.app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def owner_token(client, engine):
    from app.services.auth import hash_password

    session_factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with session_factory() as session:
        from app.db.models import Admin

        session.add(Admin(name="Owner", email="owner@test.com", password_hash=hash_password("password123"), role="owner"))
        await session.commit()

    resp = await client.post("/admin/auth/login", json={"email": "owner@test.com", "password": "password123"})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def uploader_token(client, engine):
    from app.services.auth import hash_password

    session_factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with session_factory() as session:
        from app.db.models import Admin

        session.add(Admin(name="Uploader", email="uploader@test.com", password_hash=hash_password("password123"), role="uploader"))
        await session.commit()

    resp = await client.post("/admin/auth/login", json={"email": "uploader@test.com", "password": "password123"})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]
