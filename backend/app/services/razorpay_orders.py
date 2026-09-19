"""Razorpay Orders API for the student app's native Checkout SDK flow.

Deliberately separate from services/payments.py, which the Telegram bot uses for its
Payment-Links flow - the two use different Razorpay products and different signature schemes,
and keeping them apart means neither can accidentally regress the other.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import Payment, Subscription, User, utcnow
from app.services.access import extend_subscription, get_setting, reactivate_if_bot_blocked
from app.services.payments import RAZORPAY_BASE, PaymentError

logger = logging.getLogger("app.razorpay_orders")


def _auth() -> tuple[str, str]:
    return settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET


async def create_order(db: AsyncSession, user: User) -> Payment:
    price_inr = await get_setting(db, "price_inr", 99)
    amount_paise = int(price_inr) * 100
    reference_id = f"u{user.id}_{secrets.token_hex(6)}"

    payload: dict[str, Any] = {
        "amount": amount_paise,
        "currency": "INR",
        "receipt": reference_id,
        "notes": {"user_id": str(user.id)},
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(f"{RAZORPAY_BASE}/orders", json=payload, auth=_auth())
        resp.raise_for_status()
        body = resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to create Razorpay order")
        raise PaymentError("Could not create payment order") from exc

    payment = Payment(
        user_id=user.id,
        reference_id=reference_id,
        razorpay_order_id=body["id"],
        amount_paise=amount_paise,
        status="created",
    )
    db.add(payment)
    await db.flush()
    return payment


def verify_order_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """Razorpay Orders (Checkout) signature scheme: HMAC-SHA256 of "order_id|payment_id" -
    distinct from the raw-webhook-body HMAC that payments.py::verify_webhook_signature checks."""
    if not signature or not settings.RAZORPAY_KEY_SECRET:
        return False
    payload = f"{order_id}|{payment_id}".encode("utf-8")
    expected = hmac.new(settings.RAZORPAY_KEY_SECRET.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


async def mark_order_paid(
    db: AsyncSession, order_id: str, payment_id: str
) -> tuple[Payment | None, User | None, bool]:
    """Idempotently activates a subscription for a paid order. Returns (payment, user, newly_activated).

    Structurally identical to payments.py::mark_link_paid - the single choke point called by
    both the app's client-verify endpoint and the Razorpay webhook, so whichever arrives first
    wins and the other is a safe no-op (no double-crediting).
    """
    payment = (
        await db.execute(
            select(Payment).where(Payment.razorpay_order_id == order_id).with_for_update()
        )
    ).scalar_one_or_none()
    if payment is None:
        logger.warning("Payment verification for unknown order_id=%s", order_id)
        return None, None, False

    if payment.status == "paid":
        return payment, None, False  # already processed - idempotent no-op

    user = (
        await db.execute(select(User).where(User.id == payment.user_id).with_for_update())
    ).scalar_one_or_none()
    if user is None:
        logger.error("Payment %s has no matching user", payment.id)
        return payment, None, False

    subscription_days = await get_setting(db, "subscription_days", 30)
    sub: Subscription = await extend_subscription(db, user, int(subscription_days), source="payment")
    reactivate_if_bot_blocked(user)

    payment.status = "paid"
    payment.razorpay_payment_id = payment_id
    payment.paid_at = utcnow()
    payment.subscription_id = sub.id
    await db.flush()
    return payment, user, True
