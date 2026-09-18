"""services/cache.py: get_or_set/invalidate against a fake Redis client, and the no-REDIS_URL
fallback (matches the rest of the app's "Redis is optional" convention)."""
import json

from app.config import settings
from app.services import cache


class FakeRedis:
    def __init__(self):
        self.store: dict[str, str] = {}
        self.set_calls: list[tuple[str, str, int | None]] = []

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ex=None):
        self.store[key] = value
        self.set_calls.append((key, value, ex))

    async def delete(self, *keys):
        for k in keys:
            self.store.pop(k, None)


def _use_fake_redis(monkeypatch):
    monkeypatch.setattr(settings, "REDIS_URL", "redis://fake")
    fake = FakeRedis()
    monkeypatch.setattr(cache, "_client", fake)
    monkeypatch.setattr(cache, "_client_checked", True)
    return fake


async def test_no_redis_url_always_computes(monkeypatch):
    monkeypatch.setattr(settings, "REDIS_URL", "")
    monkeypatch.setattr(cache, "_client", None)
    monkeypatch.setattr(cache, "_client_checked", False)

    calls = 0

    async def compute():
        nonlocal calls
        calls += 1
        return {"n": calls}

    first = await cache.get_or_set("k", 30, compute)
    second = await cache.get_or_set("k", 30, compute)
    assert first == {"n": 1}
    assert second == {"n": 2}  # never cached - compute() ran every time
    assert calls == 2


async def test_second_call_returns_cached_value_without_recomputing(monkeypatch):
    fake = _use_fake_redis(monkeypatch)
    calls = 0

    async def compute():
        nonlocal calls
        calls += 1
        return {"n": calls}

    first = await cache.get_or_set("dash", 20, compute)
    second = await cache.get_or_set("dash", 20, compute)
    assert first == {"n": 1}
    assert second == {"n": 1}  # cached - compute() did not run again
    assert calls == 1
    assert fake.set_calls[0][0] == "dash"
    assert fake.set_calls[0][2] == 20  # ttl passed through as `ex`
    assert json.loads(fake.store["dash"]) == {"n": 1}


async def test_different_keys_do_not_share_a_cache_entry(monkeypatch):
    _use_fake_redis(monkeypatch)

    async def compute_a():
        return {"who": "a"}

    async def compute_b():
        return {"who": "b"}

    a = await cache.get_or_set("k:a", 20, compute_a)
    b = await cache.get_or_set("k:b", 20, compute_b)
    assert a == {"who": "a"}
    assert b == {"who": "b"}


async def test_invalidate_forces_recompute(monkeypatch):
    _use_fake_redis(monkeypatch)
    calls = 0

    async def compute():
        nonlocal calls
        calls += 1
        return {"n": calls}

    await cache.get_or_set("k", 20, compute)
    await cache.invalidate("k")
    result = await cache.get_or_set("k", 20, compute)
    assert result == {"n": 2}
    assert calls == 2


async def test_redis_failure_falls_back_to_compute(monkeypatch):
    monkeypatch.setattr(settings, "REDIS_URL", "redis://fake")

    class BrokenRedis:
        async def get(self, key):
            raise ConnectionError("redis is down")

        async def set(self, key, value, ex=None):
            raise ConnectionError("redis is down")

    monkeypatch.setattr(cache, "_client", BrokenRedis())
    monkeypatch.setattr(cache, "_client_checked", True)

    result = await cache.get_or_set("k", 20, lambda: _const({"ok": True}))
    assert result == {"ok": True}  # compute() still ran and its result was returned


async def _const(value):
    return value
