"""Polls GhostlyAI.in every few minutes for new signups / new support tickets and pushes a
notification to admin devices when either count goes up.

We don't own GhostlyAI's backend, so unlike the Job Alert Bot's own events (pushed straight
from the code path that creates them - see bot/handlers/onboarding.py and support.py), this is
the only option: fetch, compare against the last-seen counts, alert on an increase.

State is a single row in app_settings under an internal ("_"-prefixed) key, so restarts don't
cause a burst of "new" notifications for things already seen. The very first run just records a
baseline and sends nothing - otherwise every one of GhostlyAI's existing users/tickets would
"arrive" as a notification the moment this ships.
"""
from __future__ import annotations

import logging

from app.db.session import session_scope
from app.services import ghostly_client as ghostly
from app.services.access import get_internal_state, set_internal_state
from app.services.ghostly_client import GhostlyApiError
from app.services.push import send_push_to_admins

logger = logging.getLogger("app.workers.ghostly_alerts")

STATE_KEY = "_ghostly_poll_state"


async def ghostly_alerts_tick() -> None:
    if not ghostly.settings.GHOSTLY_API_BASE_URL or not ghostly.settings.GHOSTLY_API_KEY:
        return  # not configured (e.g. local dev) - nothing to poll

    try:
        stats = await ghostly.get_stats()
    except GhostlyApiError:
        logger.warning("ghostly_alerts_tick: could not fetch stats", exc_info=True)
        return

    try:
        support = await ghostly.list_support()
    except GhostlyApiError:
        logger.warning("ghostly_alerts_tick: could not fetch support tickets", exc_info=True)
        support = None

    new_users_today = _first_int(stats, ["newUsersToday", "new_users_today"])
    ticket_count = len(support) if isinstance(support, list) else None

    async with session_scope() as db:
        state = await get_internal_state(db, STATE_KEY, default={}) or {}
        baseline_done = bool(state.get("baseline_done"))

        if baseline_done:
            last_new_today = state.get("last_new_users_today")
            if isinstance(last_new_today, int) and isinstance(new_users_today, int) and new_users_today > last_new_today:
                gained = new_users_today - last_new_today
                await send_push_to_admins(
                    db,
                    "New user signed up — GhostlyAI.in",
                    f"{gained} new user{'s' if gained != 1 else ''} today ({new_users_today} total today)",
                    {"type": "ghostly_new_user"},
                )

            last_ticket_count = state.get("last_ticket_count")
            if isinstance(last_ticket_count, int) and isinstance(ticket_count, int) and ticket_count > last_ticket_count:
                gained = ticket_count - last_ticket_count
                await send_push_to_admins(
                    db,
                    "New support ticket — GhostlyAI.in",
                    f"{gained} new ticket{'s' if gained != 1 else ''}",
                    {"type": "ghostly_support"},
                )

        new_state = dict(state)
        new_state["baseline_done"] = True
        if isinstance(new_users_today, int):
            new_state["last_new_users_today"] = new_users_today
        if isinstance(ticket_count, int):
            new_state["last_ticket_count"] = ticket_count
        await set_internal_state(db, STATE_KEY, new_state)
        await db.commit()


def _first_int(data: dict, keys: list[str]) -> int | None:
    if not isinstance(data, dict):
        return None
    lower = {k.lower(): v for k, v in data.items()}
    for key in keys:
        value = lower.get(key.lower())
        if isinstance(value, (int, float)):
            return int(value)
    return None
