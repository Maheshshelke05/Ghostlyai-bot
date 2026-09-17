"""Tiny in-process sliding-window limiter for the admin login endpoint.

bcrypt already makes each guess slow, but nothing stopped an attacker from hammering
/admin/auth/login. This caps failed attempts per (client IP, email) so credential stuffing
gets a 429 long before it gets anywhere. In-process is fine: the API runs as one instance,
and the worst case on a restart is a reset window.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

MAX_FAILURES = 10
WINDOW_SECONDS = 15 * 60

_failures: dict[str, deque[float]] = defaultdict(deque)


def _prune(key: str, now: float) -> deque[float]:
    q = _failures[key]
    while q and now - q[0] > WINDOW_SECONDS:
        q.popleft()
    if not q:
        _failures.pop(key, None)
        return deque()
    return q


def seconds_until_allowed(key: str) -> int:
    """0 if another attempt is allowed now, else seconds until the oldest failure expires."""
    now = time.monotonic()
    q = _prune(key, now)
    if len(q) < MAX_FAILURES:
        return 0
    return max(1, int(WINDOW_SECONDS - (now - q[0])) + 1)


def record_failure(key: str) -> None:
    _failures[key].append(time.monotonic())


def clear(key: str) -> None:
    _failures.pop(key, None)


def reset_all() -> None:
    _failures.clear()
