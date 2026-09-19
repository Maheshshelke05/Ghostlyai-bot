"""Phase D: push notifications for new matching jobs (app/workers/push_digest.py)."""
from __future__ import annotations

import json
from contextlib import asynccontextmanager

import httpx
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.services import push
from app.workers import push_digest as push_digest_module

from tests.conftest import make_job, make_user


def _session_scope_for(engine):
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)

    @asynccontextmanager
    async def scope():
        async with factory() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    return scope


_RealAsyncClient = httpx.AsyncClient


def _mock_client(handler):
    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return _RealAsyncClient(*args, **kwargs)

    return factory


async def test_push_digest_notifies_students_with_a_token(engine, db, categories, monkeypatch):
    from datetime import timedelta

    from app.db.models import utcnow

    monkeypatch.setattr(push_digest_module, "session_scope", _session_scope_for(engine))

    user = await make_user(
        db, category_slugs=["it-software"], job_types=[], trial_ends_at=utcnow() + timedelta(days=1)
    )
    user.expo_push_token = "ExponentPushToken[abc]"
    await make_job(db, categories, category_slug="it-software", title="Backend Dev", company="Acme")
    await db.commit()

    push_calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        push_calls.append(json.loads(request.content))
        return httpx.Response(200, json={"data": [{"status": "ok"}]})

    monkeypatch.setattr(push.httpx, "AsyncClient", _mock_client(handler))

    await push_digest_module.run_push_digest()

    assert len(push_calls) == 1
    assert push_calls[0][0]["title"] == "1 new job matches your profile"
    assert "Backend Dev" in push_calls[0][0]["body"]


async def test_push_digest_skips_users_without_a_token(engine, db, categories, monkeypatch):
    monkeypatch.setattr(push_digest_module, "session_scope", _session_scope_for(engine))

    await make_user(db, category_slugs=["it-software"], job_types=[])  # no push token
    await make_job(db, categories, category_slug="it-software")
    await db.commit()

    called = False

    def factory(*args, **kwargs):
        nonlocal called
        called = True
        return _RealAsyncClient(*args, **kwargs)

    monkeypatch.setattr(push.httpx, "AsyncClient", factory)
    await push_digest_module.run_push_digest()
    assert called is False


async def test_push_digest_does_not_repeat_and_matches_app_feed_ledger(engine, db, categories, monkeypatch):
    """A job already seen via GET /student/jobs (which calls ensure_deliveries) must not also
    trigger a push - both write to the same job_deliveries table."""
    from datetime import timedelta

    from app.db.models import utcnow
    from app.services.jobs import ensure_deliveries

    monkeypatch.setattr(push_digest_module, "session_scope", _session_scope_for(engine))

    user = await make_user(
        db, category_slugs=["it-software"], job_types=[], trial_ends_at=utcnow() + timedelta(days=1)
    )
    user.expo_push_token = "ExponentPushToken[abc]"
    job = await make_job(db, categories, category_slug="it-software")
    await ensure_deliveries(db, user, [job])  # simulates the student having browsed the feed
    await db.commit()

    called = False

    def factory(*args, **kwargs):
        nonlocal called
        called = True
        return _RealAsyncClient(*args, **kwargs)

    monkeypatch.setattr(push.httpx, "AsyncClient", factory)
    await push_digest_module.run_push_digest()
    assert called is False


async def test_push_digest_skips_expired_users(engine, db, categories, monkeypatch):
    from datetime import timedelta

    from app.db.models import utcnow

    monkeypatch.setattr(push_digest_module, "session_scope", _session_scope_for(engine))

    user = await make_user(
        db, category_slugs=["it-software"], job_types=[], trial_ends_at=utcnow() - timedelta(days=1)
    )
    user.expo_push_token = "ExponentPushToken[abc]"
    await make_job(db, categories, category_slug="it-software")
    await db.commit()

    called = False

    def factory(*args, **kwargs):
        nonlocal called
        called = True
        return _RealAsyncClient(*args, **kwargs)

    monkeypatch.setattr(push.httpx, "AsyncClient", factory)
    await push_digest_module.run_push_digest()
    assert called is False
