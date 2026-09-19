"""Student app native Razorpay Checkout SDK flow (Phase C): order creation, signature
verification, idempotent activation, and the webhook's defense-in-depth path."""
from __future__ import annotations

import hashlib
import hmac

import httpx

from app.config import settings
from app.db.models import Payment
from app.services.auth import create_token
from app.services.razorpay_orders import mark_order_paid, verify_order_signature

from tests.conftest import make_user


async def _student_headers(user) -> dict:
    token = create_token(user.id, "student")
    return {"Authorization": f"Bearer {token}"}


def _sign(order_id: str, payment_id: str, secret: str) -> str:
    return hmac.new(secret.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()


def test_verify_order_signature_valid_and_tampered(monkeypatch):
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "test-secret")
    good = _sign("order_abc", "pay_xyz", "test-secret")

    assert verify_order_signature("order_abc", "pay_xyz", good) is True
    assert verify_order_signature("order_abc", "pay_xyz", "0" * 64) is False
    assert verify_order_signature("order_abc", "pay_xyz", "") is False


async def test_mark_order_paid_twice_only_activates_once(db):
    user = await make_user(db)
    payment = Payment(
        user_id=user.id, reference_id="u1_order_test", razorpay_order_id="order_test1",
        amount_paise=9900, status="created",
    )
    db.add(payment)
    await db.flush()

    _, activated_user, first = await mark_order_paid(db, "order_test1", "pay_1")
    assert first is True
    assert activated_user is not None
    assert len(activated_user.subscriptions) == 1

    _, _, second = await mark_order_paid(db, "order_test1", "pay_1")
    assert second is False
    assert len(activated_user.subscriptions) == 1  # not double-credited


async def test_create_order_service_calls_razorpay_and_stores_it(db, monkeypatch):
    """Exercises razorpay_orders.create_order() directly (not through the ASGI test client,
    which is itself an httpx.AsyncClient - patching the shared httpx.AsyncClient class here
    would also break the test client's own transport)."""
    user = await make_user(db)

    async def _fake_post(self, url, json=None, auth=None):
        return httpx.Response(200, json={"id": "order_fake123"}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", _fake_post)

    from app.services.razorpay_orders import create_order

    payment = await create_order(db, user)
    assert payment.razorpay_order_id == "order_fake123"
    assert payment.amount_paise == 9900
    assert payment.status == "created"


async def test_create_order_endpoint_returns_the_service_result(client, db, monkeypatch):
    """Router-level test: mocks the service function itself so no outbound HTTP call - real or
    faked - needs to happen through the same httpx.AsyncClient the test client uses."""
    user = await make_user(db)
    await db.commit()

    async def _fake_create_order(db_, user_):
        payment = Payment(
            user_id=user_.id, reference_id="fake_ref", razorpay_order_id="order_fake123",
            amount_paise=9900, status="created",
        )
        return payment

    monkeypatch.setattr("app.api.student.payments.create_order", _fake_create_order)

    resp = await client.post("/student/payments/order", headers=await _student_headers(user))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["order_id"] == "order_fake123"
    assert body["amount"] == 9900


async def test_verify_payment_endpoint_activates_subscription(client, db, monkeypatch):
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "test-secret")
    user = await make_user(db)
    payment = Payment(
        user_id=user.id, reference_id="u2_order_test", razorpay_order_id="order_test2",
        amount_paise=9900, status="created",
    )
    db.add(payment)
    await db.commit()

    signature = _sign("order_test2", "pay_2", "test-secret")
    resp = await client.post(
        "/student/payments/verify",
        json={
            "razorpay_order_id": "order_test2",
            "razorpay_payment_id": "pay_2",
            "razorpay_signature": signature,
        },
        headers=await _student_headers(user),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["access_until"] is not None


async def test_verify_payment_rejects_tampered_signature(client, db, monkeypatch):
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "test-secret")
    user = await make_user(db)
    payment = Payment(
        user_id=user.id, reference_id="u3_order_test", razorpay_order_id="order_test3",
        amount_paise=9900, status="created",
    )
    db.add(payment)
    await db.commit()

    resp = await client.post(
        "/student/payments/verify",
        json={
            "razorpay_order_id": "order_test3",
            "razorpay_payment_id": "pay_3",
            "razorpay_signature": "0" * 64,
        },
        headers=await _student_headers(user),
    )
    assert resp.status_code == 400


async def test_webhook_payment_captured_activates_order_defense_in_depth(client, db, monkeypatch):
    """The Razorpay webhook's new payment.captured branch is a defense-in-depth backstop for
    the app's client-side /student/payments/verify call - it must independently activate an
    order-based payment (and must never touch payment_link-based payments, which never set
    razorpay_order_id)."""
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", "webhook-secret")
    user = await make_user(db)
    payment = Payment(
        user_id=user.id, reference_id="u5_order_test", razorpay_order_id="order_test5",
        amount_paise=9900, status="created",
    )
    db.add(payment)
    await db.commit()

    body = {
        "event": "payment.captured",
        "payload": {"payment": {"entity": {"id": "pay_5", "order_id": "order_test5"}}},
    }
    import json

    raw = json.dumps(body).encode()
    signature = hmac.new(b"webhook-secret", raw, hashlib.sha256).hexdigest()

    resp = await client.post(
        "/webhooks/razorpay", content=raw,
        headers={"X-Razorpay-Signature": signature, "Content-Type": "application/json"},
    )
    assert resp.status_code == 200

    await db.refresh(payment)
    assert payment.status == "paid"
    assert payment.razorpay_payment_id == "pay_5"


async def test_verify_payment_rejects_someone_elses_order(client, db, monkeypatch):
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "test-secret")
    owner = await make_user(db)
    intruder = await make_user(db)
    payment = Payment(
        user_id=owner.id, reference_id="u4_order_test", razorpay_order_id="order_test4",
        amount_paise=9900, status="created",
    )
    db.add(payment)
    await db.commit()

    signature = _sign("order_test4", "pay_4", "test-secret")
    resp = await client.post(
        "/student/payments/verify",
        json={
            "razorpay_order_id": "order_test4",
            "razorpay_payment_id": "pay_4",
            "razorpay_signature": signature,
        },
        headers=await _student_headers(intruder),
    )
    assert resp.status_code == 403
