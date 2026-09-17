"""GhostlyAI.in admin API proxy: auth gating, request shaping, config GET-merge-PUT,
and upstream-failure handling — all against a fake transport, no real network call."""
from __future__ import annotations

import json

import httpx
import pytest

from app.config import settings
from app.services import ghostly_client as ghostly


@pytest.fixture(autouse=True)
def _configure(monkeypatch):
    monkeypatch.setattr(settings, "GHOSTLY_API_BASE_URL", "https://ghostly.example/prod")
    monkeypatch.setattr(settings, "GHOSTLY_API_KEY", "test-key-123")
    monkeypatch.setattr(settings, "GHOSTLY_API_AUTH_HEADER", "x-api-key")


_RealAsyncClient = httpx.AsyncClient


def _mock_client(handler):
    """Patches ghostly_client.httpx.AsyncClient so every request goes through `handler`
    instead of the network, keeping the real timeout/base_url call signature intact.
    Must use the real class captured above `httpx` is a shared module, so patching
    `httpx.AsyncClient` and then calling `httpx.AsyncClient` from inside would recurse."""

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return _RealAsyncClient(*args, **kwargs)

    return factory


async def _auth_header(client, owner_token):
    return {"Authorization": f"Bearer {owner_token}"}


# ---------------------------------------------------------------------------
# Role gating
# ---------------------------------------------------------------------------
async def test_uploader_forbidden(client, uploader_token):
    resp = await client.get("/admin/ghostly/stats", headers={"Authorization": f"Bearer {uploader_token}"})
    assert resp.status_code == 403


async def test_no_token_unauthorized(client):
    resp = await client.get("/admin/ghostly/stats")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Auth header + request shaping
# ---------------------------------------------------------------------------
async def test_stats_sends_configured_header_and_full_param(client, owner_token, monkeypatch):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["headers"] = dict(request.headers)
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"total_users": 42})

    monkeypatch.setattr(ghostly.httpx, "AsyncClient", _mock_client(handler))

    resp = await client.get("/admin/ghostly/stats", headers={"Authorization": f"Bearer {owner_token}"})
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"total_users": 42}
    assert seen["headers"]["x-api-key"] == "test-key-123"
    assert "full=1" in seen["url"]


async def test_authorization_header_gets_bearer_prefix(client, owner_token, monkeypatch):
    settings_module = ghostly.settings
    monkeypatch.setattr(settings_module, "GHOSTLY_API_AUTH_HEADER", "Authorization")
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={})

    monkeypatch.setattr(ghostly.httpx, "AsyncClient", _mock_client(handler))
    resp = await client.get("/admin/ghostly/stats", headers={"Authorization": f"Bearer {owner_token}"})
    assert resp.status_code == 200
    assert seen["auth"] == "Bearer test-key-123"


async def test_search_and_filter_params_forwarded(client, owner_token, monkeypatch):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"items": []})

    monkeypatch.setattr(ghostly.httpx, "AsyncClient", _mock_client(handler))
    resp = await client.get(
        "/admin/ghostly/users",
        params={"search": "someone@example.com"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp.status_code == 200
    assert "search=someone" in seen["url"]

    resp = await client.get(
        "/admin/ghostly/users",
        params={"filter": "new_today"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp.status_code == 200
    assert "filter=new_today" in seen["url"]


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------
async def test_update_user_plan_forwards_body(client, owner_token, monkeypatch):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(ghostly.httpx, "AsyncClient", _mock_client(handler))
    resp = await client.put(
        "/admin/ghostly/users/u123/plan",
        json={"plan": "PRO", "days": 30},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp.status_code == 200, resp.text
    assert seen["method"] == "PUT"
    assert seen["path"] == "/prod/admin/users/u123/plan"
    assert seen["body"] == {"plan": "pro", "days": 30}  # plan lowercased by the schema


async def test_update_user_plan_rejects_empty_body(client, owner_token):
    resp = await client.put(
        "/admin/ghostly/users/u123/plan", json={}, headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert resp.status_code == 400


async def test_send_email_validates_and_forwards(client, owner_token, monkeypatch):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"sent": True})

    monkeypatch.setattr(ghostly.httpx, "AsyncClient", _mock_client(handler))
    resp = await client.post(
        "/admin/ghostly/send-email",
        json={"to": "student@example.com", "subject": "Hi", "body": "Hello there"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp.status_code == 200, resp.text
    assert seen["body"]["to"] == "student@example.com"

    bad = await client.post(
        "/admin/ghostly/send-email",
        json={"to": "not-an-email", "subject": "Hi", "body": "x"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert bad.status_code == 422


async def test_support_reply_and_status_update(client, owner_token, monkeypatch):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path, json.loads(request.content or b"{}")))
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(ghostly.httpx, "AsyncClient", _mock_client(handler))

    resp = await client.post(
        "/admin/ghostly/support/t1/reply",
        json={"text": "We're on it", "resolve": True},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp.status_code == 200, resp.text

    resp = await client.put(
        "/admin/ghostly/support/t1",
        json={"status": "reopened"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp.status_code == 200, resp.text

    assert calls[0] == ("POST", "/prod/admin/support/t1/reply", {"text": "We're on it", "resolve": True})
    assert calls[1] == ("PUT", "/prod/admin/support/t1", {"status": "reopened"})


async def test_announcement_create_and_send(client, owner_token, monkeypatch):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else None
        calls.append((request.method, request.url.path, body))
        if request.method == "POST" and request.url.path.endswith("/announcements"):
            return httpx.Response(200, json={"id": "ann1", "title": "Diwali offer"})
        return httpx.Response(200, json={"sent_to": 500})

    monkeypatch.setattr(ghostly.httpx, "AsyncClient", _mock_client(handler))

    resp = await client.post(
        "/admin/ghostly/announcements",
        json={"title": "Diwali offer", "body": "50% off"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp.status_code == 200, resp.text
    ann_id = resp.json()["id"]

    resp = await client.post(
        f"/admin/ghostly/announcements/{ann_id}/send",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"sent_to": 500}
    assert calls[0] == ("POST", "/prod/admin/announcements", {"title": "Diwali offer", "message": "50% off"})
    assert calls[-1][:2] == ("POST", "/prod/admin/announcements/ann1/send")


# ---------------------------------------------------------------------------
# Config: GET-merge-PUT (upstream replaces the whole doc, so we must not clobber it)
# ---------------------------------------------------------------------------
async def test_config_patch_merges_onto_current_before_put(client, owner_token, monkeypatch):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            calls.append(("GET", None))
            return httpx.Response(200, json={"ai_auto_reply": False, "welcome_message": "Hi!", "max_free_days": 7})
        body = json.loads(request.content)
        calls.append(("PUT", body))
        return httpx.Response(200, json=body)

    monkeypatch.setattr(ghostly.httpx, "AsyncClient", _mock_client(handler))

    resp = await client.put(
        "/admin/ghostly/config",
        json={"ai_auto_reply": True},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp.status_code == 200, resp.text
    result = resp.json()
    # the fields we didn't touch must survive the round trip
    assert result == {"ai_auto_reply": True, "welcome_message": "Hi!", "max_free_days": 7}
    assert calls[0][0] == "GET"
    assert calls[1] == ("PUT", result)


# ---------------------------------------------------------------------------
# Upstream failure handling
# ---------------------------------------------------------------------------
async def test_upstream_401_becomes_502_with_helpful_message(client, owner_token, monkeypatch):
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "Unauthorized"})

    monkeypatch.setattr(ghostly.httpx, "AsyncClient", _mock_client(handler))
    resp = await client.get("/admin/ghostly/stats", headers={"Authorization": f"Bearer {owner_token}"})
    assert resp.status_code == 502
    assert "API key" in resp.json()["detail"]


async def test_upstream_timeout_becomes_504(client, owner_token, monkeypatch):
    def raise_timeout(*args, **kwargs):
        raise httpx.TimeoutException("boom")

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def request(self, *a, **k):
            raise httpx.TimeoutException("boom")

    monkeypatch.setattr(ghostly.httpx, "AsyncClient", _Client)
    resp = await client.get("/admin/ghostly/stats", headers={"Authorization": f"Bearer {owner_token}"})
    assert resp.status_code == 504


async def test_missing_key_returns_503(client, owner_token, monkeypatch):
    monkeypatch.setattr(settings, "GHOSTLY_API_KEY", "")
    resp = await client.get("/admin/ghostly/stats", headers={"Authorization": f"Bearer {owner_token}"})
    assert resp.status_code == 503
