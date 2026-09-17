"""Client for the GhostlyAI.in admin API — a second product's data, surfaced read-only(ish)
inside our own admin app under Settings > "GhotlyAI.in".

The mobile app never sees `GHOSTLY_API_KEY` — every call is proxied through our own
`/admin/ghostly/*` routes (owner-only), which use this module to talk to the upstream API.
That keeps the key server-side and reuses our own JWT auth for the app.

The upstream auth header is a custom one checked directly in their Lambda code, not a
standard AWS authorizer: `x-admin-secret` (confirmed with their developer). It's read from
`GHOSTLY_API_AUTH_HEADER` rather than hardcoded, in case it's ever rotated to something else.
"""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

import httpx

from app.config import settings

logger = logging.getLogger("app.ghostly")

_TIMEOUT = 20.0


class GhostlyApiError(Exception):
    """Raised for any failure talking to the upstream GhostlyAI API. `status_code` is the
    HTTP status our own API should respond with (never a raw 5xx passthrough of an upstream
    4xx, so the app can tell "your input was bad" apart from "GhostlyAI.in is unreachable")."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _auth_headers() -> dict[str, str]:
    if not settings.GHOSTLY_API_KEY:
        raise GhostlyApiError(503, "GHOSTLY_API_KEY is not configured on the server")
    header = (settings.GHOSTLY_API_AUTH_HEADER or "x-api-key").strip()
    value = settings.GHOSTLY_API_KEY
    if header.lower() == "authorization" and not value.lower().startswith("bearer "):
        value = f"Bearer {value}"
    return {header: value}


async def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
) -> Any:
    base = settings.GHOSTLY_API_BASE_URL.rstrip("/")
    if not base:
        raise GhostlyApiError(503, "GHOSTLY_API_BASE_URL is not configured on the server")

    url = f"{base}{path}"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.request(method, url, params=params, json=json, headers=_auth_headers())
    except httpx.TimeoutException:
        logger.warning("GhostlyAI API timed out: %s %s", method, path)
        raise GhostlyApiError(504, "GhostlyAI.in server did not respond in time")
    except httpx.HTTPError as exc:
        logger.warning("GhostlyAI API request failed: %s %s - %s", method, path, exc)
        raise GhostlyApiError(502, "Could not reach the GhostlyAI.in server")

    if resp.status_code in (401, 403):
        logger.warning("GhostlyAI API auth rejected (%s): %s %s", resp.status_code, method, path)
        raise GhostlyApiError(
            502,
            "GhostlyAI.in rejected the API key. Check GHOSTLY_API_KEY and "
            "GHOSTLY_API_AUTH_HEADER in the backend .env.",
        )
    if resp.status_code >= 400:
        detail = (resp.text or "").strip()[:300] or f"GhostlyAI.in API error {resp.status_code}"
        logger.warning("GhostlyAI API error %s on %s %s: %s", resp.status_code, method, path, detail)
        # upstream 4xx (bad input) maps to 400 for our client; anything else is a 502
        raise GhostlyApiError(400 if resp.status_code < 500 else 502, detail)

    if not resp.content:
        return {}
    try:
        return resp.json()
    except ValueError:
        return {"raw": resp.text}


# ---------------------------------------------------------------------------
# Read-only
# ---------------------------------------------------------------------------
async def get_stats() -> Any:
    return await _request("GET", "/admin/stats", params={"full": 1})


async def list_users(search: str | None = None, filter: str | None = None) -> Any:
    params: dict[str, Any] = {}
    if search:
        params["search"] = search
    if filter:
        params["filter"] = filter
    return await _request("GET", "/admin/users", params=params)


async def list_support() -> Any:
    return await _request("GET", "/admin/support")


async def get_email_stats() -> Any:
    return await _request("GET", "/admin/email-stats")


async def list_announcements() -> Any:
    return await _request("GET", "/admin/announcements")


async def get_config() -> Any:
    return await _request("GET", "/admin/config")


# ---------------------------------------------------------------------------
# Mutating
# ---------------------------------------------------------------------------
async def update_user_plan(user_id: str, payload: dict[str, Any]) -> Any:
    return await _request("PUT", f"/admin/users/{quote(user_id, safe='')}/plan", json=payload)


async def send_email(payload: dict[str, Any]) -> Any:
    return await _request("POST", "/admin/send-email", json=payload)


async def create_announcement(payload: dict[str, Any]) -> Any:
    return await _request("POST", "/admin/announcements", json=payload)


async def send_announcement(announcement_id: str) -> Any:
    return await _request("POST", f"/admin/announcements/{quote(announcement_id, safe='')}/send")


async def reply_support(ticket_id: str, payload: dict[str, Any]) -> Any:
    # Ticket ids look like "107501432674953932232#2026-09-17" - the raw "#" makes httpx treat
    # everything after it (including "/reply") as a URL fragment and silently drop it from the
    # actual request, so this MUST be quoted rather than embedded raw. (Confirmed live: the
    # unquoted version resolved to POST /admin/support/107501432674953932232 with no /reply at
    # all - this is why replying from the app was silently failing.)
    return await _request("POST", f"/admin/support/{quote(ticket_id, safe='')}/reply", json=payload)


async def update_support(ticket_id: str, payload: dict[str, Any]) -> Any:
    return await _request("PUT", f"/admin/support/{quote(ticket_id, safe='')}", json=payload)


async def update_config(patch: dict[str, Any]) -> Any:
    """PUT /admin/config replaces the whole document upstream (no server-side merge), so this
    does the GET-merge-PUT dance here — the same thing their own bot does — so a mobile client
    changing one field (e.g. the AI auto-reply toggle) can never wipe out the rest of the config."""
    current = await get_config()
    if not isinstance(current, dict):
        current = {}
    merged = {**current, **patch}
    return await _request("PUT", "/admin/config", json=merged)
