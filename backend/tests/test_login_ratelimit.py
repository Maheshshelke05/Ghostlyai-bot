"""Login brute-force protection: failures are counted per (ip, email), success clears them."""
import pytest

from app.services import ratelimit


@pytest.fixture(autouse=True)
def _clean():
    ratelimit.reset_all()
    yield
    ratelimit.reset_all()


def test_allows_until_limit_then_blocks():
    key = "1.2.3.4|owner@example.com"
    for _ in range(ratelimit.MAX_FAILURES):
        assert ratelimit.seconds_until_allowed(key) == 0
        ratelimit.record_failure(key)
    wait = ratelimit.seconds_until_allowed(key)
    assert 0 < wait <= ratelimit.WINDOW_SECONDS + 1


def test_success_clears_and_other_keys_are_independent():
    key, other = "1.2.3.4|owner@example.com", "9.9.9.9|owner@example.com"
    for _ in range(ratelimit.MAX_FAILURES):
        ratelimit.record_failure(key)
    assert ratelimit.seconds_until_allowed(key) > 0
    assert ratelimit.seconds_until_allowed(other) == 0
    ratelimit.clear(key)
    assert ratelimit.seconds_until_allowed(key) == 0


def test_old_failures_expire(monkeypatch):
    key = "1.2.3.4|owner@example.com"
    t = [1000.0]
    monkeypatch.setattr(ratelimit.time, "monotonic", lambda: t[0])
    for _ in range(ratelimit.MAX_FAILURES):
        ratelimit.record_failure(key)
    assert ratelimit.seconds_until_allowed(key) > 0
    t[0] += ratelimit.WINDOW_SECONDS + 1
    assert ratelimit.seconds_until_allowed(key) == 0
