"""T28-T32: admin auth, RBAC, settings validation, dashboard, Telegram webhook secret (Chapter 21.1)."""
from app.config import settings


async def test_login_wrong_password_returns_401(client, owner_token):
    resp = await client.post("/admin/auth/login", json={"email": "owner@test.com", "password": "wrong-password"})
    assert resp.status_code == 401


async def test_uploader_cannot_list_users(client, uploader_token):
    resp = await client.get("/admin/users", headers={"Authorization": f"Bearer {uploader_token}"})
    assert resp.status_code == 403


async def test_owner_can_list_users(client, owner_token):
    resp = await client.get("/admin/users", headers={"Authorization": f"Bearer {owner_token}"})
    assert resp.status_code == 200
    assert "items" in resp.json()


async def test_settings_invalid_digest_time_returns_422(client, owner_token):
    resp = await client.put(
        "/admin/settings", json={"digest_times": ["25:00"]},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp.status_code == 422


async def test_settings_valid_update_roundtrip(client, owner_token):
    headers = {"Authorization": f"Bearer {owner_token}"}
    resp = await client.put("/admin/settings", json={"price_inr": 149}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["price_inr"] == 149

    resp = await client.get("/admin/settings", headers=headers)
    assert resp.json()["price_inr"] == 149


async def test_dashboard_returns_expected_shape(client, owner_token):
    resp = await client.get("/admin/dashboard", headers={"Authorization": f"Bearer {owner_token}"})
    assert resp.status_code == 200
    body = resp.json()
    for key in ("users", "subscriptions", "revenue_inr", "jobs", "deliveries", "last_7_days"):
        assert key in body
    assert len(body["last_7_days"]) == 7


async def test_telegram_webhook_wrong_secret_returns_403(client, monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", "the-real-secret")
    resp = await client.post(
        "/webhooks/telegram",
        json={"update_id": 1},
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"},
    )
    assert resp.status_code == 403


async def test_telegram_webhook_correct_secret_returns_200(client, monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", "the-real-secret")
    resp = await client.post(
        "/webhooks/telegram",
        json={"update_id": 1},
        headers={"X-Telegram-Bot-Api-Secret-Token": "the-real-secret"},
    )
    assert resp.status_code == 200
