"""Push notifications: token storage/registration, Expo send, the GhostlyAI poll job's
baseline/increase logic, and the two Job Alert Bot event hooks that fire pushes directly."""
import json
from contextlib import asynccontextmanager

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import settings
from app.db.models import Admin, SupportMessage
from app.services import ghostly_client as ghostly
from app.services import push
from app.services.access import get_internal_state
from app.workers import ghostly_alerts as ghostly_alerts_module
from app.workers.ghostly_alerts import STATE_KEY, ghostly_alerts_tick

from tests.conftest import FakeBot, make_user


def _session_scope_for(engine):
    """ghostly_alerts_tick() opens its own sessions via session_scope() (it isn't handed one,
    since it also runs unattended from APScheduler) - point that at the test engine instead of
    the real production one, the same way test_e2e_fake_users.py does for the digest worker."""
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


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


_RealAsyncClient = httpx.AsyncClient


def _mock_client(handler):
    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return _RealAsyncClient(*args, **kwargs)

    return factory


# ---------------------------------------------------------------------------
# services/push.py
# ---------------------------------------------------------------------------
async def test_get_admin_push_tokens_filters_inactive_and_empty(db):
    db.add(Admin(name="A", email="a@x.com", password_hash="x", role="owner", is_active=True, expo_push_token="tokA"))
    db.add(Admin(name="B", email="b@x.com", password_hash="x", role="uploader", is_active=True, expo_push_token=None))
    db.add(Admin(name="C", email="c@x.com", password_hash="x", role="owner", is_active=False, expo_push_token="tokC"))
    db.add(Admin(name="D", email="d@x.com", password_hash="x", role="owner", is_active=True, expo_push_token="tokD"))
    await db.flush()

    tokens = await push.get_admin_push_tokens(db)
    assert sorted(tokens) == ["tokA", "tokD"]


async def test_get_admin_push_tokens_excludes_given_admin(db):
    a = Admin(name="A", email="a2@x.com", password_hash="x", role="owner", is_active=True, expo_push_token="tokA")
    db.add(a)
    await db.flush()
    tokens = await push.get_admin_push_tokens(db, exclude_admin_id=a.id)
    assert tokens == []


async def test_send_push_to_admins_posts_expo_shape(db, monkeypatch):
    db.add(Admin(name="A", email="a3@x.com", password_hash="x", role="owner", is_active=True, expo_push_token="tokA"))
    await db.flush()

    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"data": [{"status": "ok"}]})

    monkeypatch.setattr(push.httpx, "AsyncClient", _mock_client(handler))
    await push.send_push_to_admins(db, "Title", "Body", {"type": "x"})

    assert seen["url"] == push.EXPO_PUSH_URL
    assert seen["body"] == [{"to": "tokA", "title": "Title", "body": "Body", "data": {"type": "x"}, "sound": "default", "priority": "high"}]


async def test_send_push_to_admins_no_tokens_makes_no_request(db, monkeypatch):
    called = False

    def factory(*args, **kwargs):
        nonlocal called
        called = True
        return _RealAsyncClient(*args, **kwargs)

    monkeypatch.setattr(push.httpx, "AsyncClient", factory)
    await push.send_push_to_admins(db, "Title", "Body")
    assert called is False


async def test_send_push_to_admins_swallows_network_errors(db, monkeypatch):
    db.add(Admin(name="A", email="a4@x.com", password_hash="x", role="owner", is_active=True, expo_push_token="tokA"))
    await db.flush()

    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(push.httpx, "AsyncClient", _mock_client(handler))
    await push.send_push_to_admins(db, "Title", "Body")  # must not raise


# ---------------------------------------------------------------------------
# PUT /admin/auth/push-token
# ---------------------------------------------------------------------------
async def test_set_push_token_endpoint(client, owner_token, engine):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    resp = await client.put("/admin/auth/push-token", json={"token": "ExponentPushToken[abc]"}, headers=_auth(owner_token))
    assert resp.status_code == 200, resp.text

    session_factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with session_factory() as s:
        admin = (await s.execute(select(Admin).where(Admin.email == "owner@test.com"))).scalar_one()
        assert admin.expo_push_token == "ExponentPushToken[abc]"

    # empty clears it
    resp = await client.put("/admin/auth/push-token", json={"token": ""}, headers=_auth(owner_token))
    assert resp.status_code == 200, resp.text
    async with session_factory() as s:
        admin = (await s.execute(select(Admin).where(Admin.email == "owner@test.com"))).scalar_one()
        assert admin.expo_push_token is None


async def test_set_push_token_requires_auth(client):
    resp = await client.put("/admin/auth/push-token", json={"token": "x"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GhostlyAI poll job: baseline, then alert only on real increases
# ---------------------------------------------------------------------------
def _configure_ghostly(monkeypatch):
    monkeypatch.setattr(settings, "GHOSTLY_API_BASE_URL", "https://ghostly.example/prod")
    monkeypatch.setattr(settings, "GHOSTLY_API_KEY", "k")
    monkeypatch.setattr(settings, "GHOSTLY_API_AUTH_HEADER", "x-admin-secret")


async def test_ghostly_alerts_first_run_only_baselines(engine, monkeypatch):
    _configure_ghostly(monkeypatch)
    monkeypatch.setattr(ghostly_alerts_module, "session_scope", _session_scope_for(engine))
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with factory() as s:
        s.add(Admin(name="A", email="a5@x.com", password_hash="x", role="owner", is_active=True, expo_push_token="tokA"))
        await s.commit()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/stats"):
            return httpx.Response(200, json={"newUsersToday": 5})
        if request.url.path.endswith("/support"):
            return httpx.Response(200, json=[{"id": "t1"}, {"id": "t2"}])
        raise AssertionError(f"unexpected push during baseline run: {request.url}")

    monkeypatch.setattr(ghostly.httpx, "AsyncClient", _mock_client(handler))
    await ghostly_alerts_tick()

    async with factory() as s:
        state = await get_internal_state(s, STATE_KEY)
    assert state == {"baseline_done": True, "last_new_users_today": 5, "last_ticket_count": 2}


async def test_ghostly_alerts_increase_triggers_push_then_settles(engine, monkeypatch):
    _configure_ghostly(monkeypatch)
    monkeypatch.setattr(ghostly_alerts_module, "session_scope", _session_scope_for(engine))
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with factory() as s:
        s.add(Admin(name="A", email="a6@x.com", password_hash="x", role="owner", is_active=True, expo_push_token="tokA"))
        await s.commit()

    counts = {"users": 5, "tickets": 2}
    push_calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/stats"):
            return httpx.Response(200, json={"newUsersToday": counts["users"]})
        if request.url.path.endswith("/support"):
            return httpx.Response(200, json=[{"id": f"t{i}"} for i in range(counts["tickets"])])
        if "exp.host" in str(request.url) or request.url.host == "exp.host":
            push_calls.append(json.loads(request.content))
            return httpx.Response(200, json={"data": [{"status": "ok"}]})
        raise AssertionError(f"unexpected request: {request.url}")

    mock = _mock_client(handler)
    monkeypatch.setattr(ghostly.httpx, "AsyncClient", mock)
    monkeypatch.setattr(push.httpx, "AsyncClient", mock)

    await ghostly_alerts_tick()  # baseline, no push
    assert push_calls == []

    counts["users"] = 8
    counts["tickets"] = 3
    await ghostly_alerts_tick()  # both increased -> two pushes
    assert len(push_calls) == 2
    bodies = {c[0]["title"]: c[0]["body"] for c in push_calls}
    assert "3 new users today (8 total today)" in bodies["New user signed up — GhostlyAI.in"]
    assert "1 new ticket" in bodies["New support ticket — GhostlyAI.in"]

    push_calls.clear()
    await ghostly_alerts_tick()  # unchanged -> no push
    assert push_calls == []


async def test_ghostly_alerts_skips_when_not_configured(db, monkeypatch):
    monkeypatch.setattr(settings, "GHOSTLY_API_BASE_URL", "")
    await ghostly_alerts_tick()  # must not raise, nothing to assert - just no crash


# ---------------------------------------------------------------------------
# Job Alert Bot event hooks actually fire a push
# ---------------------------------------------------------------------------
async def test_finish_onboarding_pushes_admins_on_first_completion(db, monkeypatch):
    from app.bot.handlers import onboarding as onboarding_handlers
    from app.db.seed import seed_all
    from app.db.models import Category, User

    await seed_all(db)
    acc = (await db.execute(select(Category).where(Category.slug == "accounts-finance"))).scalar_one()
    student = await make_user(db, status="onboarding", trial_ends_at=None)

    calls = []

    async def fake_push(db_, title, body, data=None, **kw):
        calls.append((title, body))

    monkeypatch.setattr(onboarding_handlers, "send_push_to_admins", fake_push)

    class _Msg:
        bot = FakeBot()

        async def answer(self, text, reply_markup=None):
            pass

    class _State:
        def __init__(self, data):
            self._data = data

        async def get_data(self):
            return self._data

        async def clear(self):
            self._data = {}

    user = await db.get(User, student.id)
    state = _State({"selected_category_ids": [acc.id], "selected_job_types": ["private"]})
    await onboarding_handlers._finish_onboarding(_Msg(), state, db, user, "en")

    assert calls and calls[0][0] == "New student signed up"


async def test_support_text_pushes_admins(db, monkeypatch):
    from app.bot.handlers import support as support_handlers

    user = await make_user(db, status="active", category_slugs=["accounts-finance"])
    calls = []

    async def fake_push(db_, title, body, data=None, **kw):
        calls.append((title, body))

    monkeypatch.setattr(support_handlers, "send_push_to_admins", fake_push)

    class _Msg:
        text = "The apply link for job 12 is broken"

        async def answer(self, text, reply_markup=None):
            pass

    class _State:
        async def clear(self):
            pass

    await support_handlers.on_support_text(_Msg(), _State(), db, user)

    assert (await db.execute(select(SupportMessage))).scalars().all()
    assert calls and calls[0][0].startswith("New support message")
