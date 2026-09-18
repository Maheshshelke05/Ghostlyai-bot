"""Polls GhostlyAI.in every few minutes for new signups / new support tickets and pushes a
notification to admin devices naming who signed up / what came in - not just a bare count.

We don't own GhostlyAI's backend, so unlike the Job Alert Bot's own events (pushed straight
from the code path that creates them - see bot/handlers/onboarding.py and support.py), this is
the only option: fetch, compare against the last-seen ids, alert on what's actually new.

State is a single row in app_settings under an internal ("_"-prefixed) key: the set of user/
ticket ids already seen, so restarts don't cause a burst of "new" notifications for things
already seen, and IDs (not just counts) mean a tick with 2 new signups and 1 departure (e.g. a
user dropping out of "new today" as the day rolls over) still correctly reports "2 new", not "1
new" from a naive count delta. The very first run just records a baseline and sends nothing -
otherwise every one of GhostlyAI's existing users/tickets would "arrive" as a notification the
moment this ships.
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
# Keeps the stored state small: only this many most-recent ids are remembered per category,
# which is far more than could plausibly arrive between two 5-minute polls.
MAX_TRACKED_IDS = 500


def _names_summary(names: list[str], noun: str) -> str:
    if len(names) == 1:
        return names[0]
    if len(names) <= 3:
        return ", ".join(names)
    return f"{', '.join(names[:3])} and {len(names) - 3} more {noun}"


async def ghostly_alerts_tick() -> None:
    if not ghostly.settings.GHOSTLY_API_BASE_URL or not ghostly.settings.GHOSTLY_API_KEY:
        return  # not configured (e.g. local dev) - nothing to poll

    try:
        users_payload = await ghostly.list_users(filter="new_today")
        new_today_users = _extract_list(users_payload)
    except GhostlyApiError:
        logger.warning("ghostly_alerts_tick: could not fetch new-today users", exc_info=True)
        new_today_users = None

    try:
        support = await ghostly.list_support()
    except GhostlyApiError:
        logger.warning("ghostly_alerts_tick: could not fetch support tickets", exc_info=True)
        support = None

    async with session_scope() as db:
        state = await get_internal_state(db, STATE_KEY, default={}) or {}
        baseline_done = bool(state.get("baseline_done"))
        new_state = dict(state)

        if new_today_users is not None:
            current_ids = {str(u.get("user_id") or u.get("id")) for u in new_today_users if u.get("user_id") or u.get("id")}
            seen_ids = set(state.get("seen_new_user_ids") or [])
            if baseline_done:
                new_ids = current_ids - seen_ids
                if new_ids:
                    names = [
                        str(u.get("name") or u.get("email") or "Someone")
                        for u in new_today_users
                        if str(u.get("user_id") or u.get("id")) in new_ids
                    ]
                    await send_push_to_admins(
                        db,
                        f"{len(new_ids)} new user{'s' if len(new_ids) != 1 else ''} signed up — GhostlyAI.in",
                        _names_summary(names, "users"),
                        {"type": "ghostly_new_user"},
                    )
            new_state["seen_new_user_ids"] = list(current_ids)[-MAX_TRACKED_IDS:]

        if isinstance(support, list):
            current_tickets = {str(t.get("id")): t for t in support if t.get("id")}
            seen_ticket_ids = set(state.get("seen_ticket_ids") or [])
            if baseline_done:
                new_ticket_ids = set(current_tickets) - seen_ticket_ids
                if new_ticket_ids:
                    subjects = [
                        str(current_tickets[tid].get("subject") or current_tickets[tid].get("user_name") or "New ticket")
                        for tid in new_ticket_ids
                    ]
                    await send_push_to_admins(
                        db,
                        f"{len(new_ticket_ids)} new support ticket{'s' if len(new_ticket_ids) != 1 else ''} — GhostlyAI.in",
                        _names_summary(subjects, "tickets"),
                        {"type": "ghostly_support"},
                    )
            new_state["seen_ticket_ids"] = list(current_tickets)[-MAX_TRACKED_IDS:]

        new_state["baseline_done"] = True
        await set_internal_state(db, STATE_KEY, new_state)
        await db.commit()


def _extract_list(payload) -> list[dict] | None:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for value in payload.values():
            if isinstance(value, list):
                return value
    return None
