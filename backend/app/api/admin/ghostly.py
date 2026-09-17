"""Proxy for the GhostlyAI.in admin API, surfaced inside our own admin app.

Everything here mirrors the endpoints documented for GhostlyAI.in's own admin bot:
stats, users, support tickets, email stats/send, announcements, config. Owner-only —
this is another product's user data (emails, plans, support messages), same sensitivity
class as our own support inbox.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.api.admin.deps import owner_only
from app.api.admin.schemas import (
    GhostlyAnnouncementIn,
    GhostlyConfigIn,
    GhostlySendEmailIn,
    GhostlySupportReplyIn,
    GhostlySupportUpdateIn,
    GhostlyUserPlanIn,
)
from app.db.models import Admin
from app.services import ghostly_client as ghostly
from app.services.ghostly_client import GhostlyApiError

router = APIRouter(prefix="/admin/ghostly", tags=["admin-ghostly"])


async def _call(coro):
    try:
        return await coro
    except GhostlyApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.get("/stats")
async def stats(_admin: Admin = Depends(owner_only)) -> Any:
    return await _call(ghostly.get_stats())


@router.get("/users")
async def users(
    search: str | None = None,
    filter: str | None = None,
    _admin: Admin = Depends(owner_only),
) -> Any:
    return await _call(ghostly.list_users(search=search, filter=filter))


@router.put("/users/{user_id}/plan")
async def update_user_plan(
    user_id: str, payload: GhostlyUserPlanIn, _admin: Admin = Depends(owner_only)
) -> Any:
    body = payload.model_dump(exclude_none=True)
    if not body:
        raise HTTPException(status_code=400, detail="Nothing to update")
    return await _call(ghostly.update_user_plan(user_id, body))


@router.get("/support")
async def support(_admin: Admin = Depends(owner_only)) -> Any:
    return await _call(ghostly.list_support())


@router.post("/support/{ticket_id}/reply")
async def support_reply(
    ticket_id: str, payload: GhostlySupportReplyIn, _admin: Admin = Depends(owner_only)
) -> Any:
    # Confirmed live: the reply endpoint wants "message", not "text" (error was literally
    # {"success": false, "error": "Missing 'message'"}) - same field-naming convention as
    # announcements. GhostlySupportReplyIn keeps "text" as our own API's name for consistency.
    return await _call(
        ghostly.reply_support(ticket_id, {"message": payload.text, "resolve": payload.resolve})
    )


@router.put("/support/{ticket_id}")
async def support_update(
    ticket_id: str, payload: GhostlySupportUpdateIn, _admin: Admin = Depends(owner_only)
) -> Any:
    return await _call(ghostly.update_support(ticket_id, payload.model_dump()))


@router.get("/email-stats")
async def email_stats(_admin: Admin = Depends(owner_only)) -> Any:
    return await _call(ghostly.get_email_stats())


@router.post("/send-email")
async def send_email(payload: GhostlySendEmailIn, _admin: Admin = Depends(owner_only)) -> Any:
    return await _call(ghostly.send_email(payload.model_dump()))


@router.get("/announcements")
async def announcements(_admin: Admin = Depends(owner_only)) -> Any:
    return await _call(ghostly.list_announcements())


@router.post("/announcements")
async def create_announcement(
    payload: GhostlyAnnouncementIn, _admin: Admin = Depends(owner_only)
) -> Any:
    # Confirmed live: an announcement's text field is "message", not "body" - GhostlyAnnouncementIn
    # keeps "body" as our own API's field name (consistent with the rest of this app), mapped here.
    return await _call(ghostly.create_announcement({"title": payload.title, "message": payload.body}))


@router.post("/announcements/{announcement_id}/send")
async def send_announcement(announcement_id: str, _admin: Admin = Depends(owner_only)) -> Any:
    return await _call(ghostly.send_announcement(announcement_id))


@router.get("/config")
async def config(_admin: Admin = Depends(owner_only)) -> Any:
    return await _call(ghostly.get_config())


@router.put("/config")
async def update_config(payload: GhostlyConfigIn, _admin: Admin = Depends(owner_only)) -> Any:
    patch = payload.model_dump(exclude_none=True)
    return await _call(ghostly.update_config(patch))
