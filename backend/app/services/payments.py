"""Razorpay payment links: create, verify webhook signatures, idempotent activation (Chapter 11)."""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import time
from datetime import timedelta
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import Payment, Subscription, User, utcnow
from app.services.access import extend_subscription, get_setting, reactivate_if_bot_blocked

logger = logging.getLogger("app.payments")

RAZORPAY_BASE = "https://api.razorpay.com/v1"
_LINK_REUSE_MIN_MINUTES = 30


class PaymentError(Exception):
    pass


def _auth() -> tuple[str, str]:
    return settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET


async def get_or_create_payment_link(db: AsyncSession, user: User) -> Payment:
    """Reuses a not-yet-paid link valid for 30+ more minutes, else creates a new one."""
    now = utcnow()
    reuse_cutoff = now + timedelta(minutes=_LINK_REUSE_MIN_MINUTES)

    existing = (
        await db.execute(
            select(Payment)
            .where(
                Payment.user_id == user.id,
                Payment.status == "created",
                Payment.expires_at.is_not(None),
                Payment.expires_at > reuse_cutoff,
            )
            .order_by(Payment.created_at.desc())
        )
    ).scalars().first()
    if existing is not None:
        return existing

    price_inr = await get_setting(db, "price_inr", 99)
    subscription_days = await get_setting(db, "subscription_days", 30)

    reference_id = f"u{user.id}_{secrets.token_hex(6)}"
    expire_by = int(time.time()) + 24 * 3600

    payload: dict[str, Any] = {
        "amount": int(price_inr) * 100,
        "currency": "INR",
        "accept_partial": False,
        "description": f"Job alerts subscription - {subscription_days} days",
        "reference_id": reference_id,
        "expire_by": expire_by,
        "reminder_enable": False,
        "notify": {"sms": False, "email": False},
        "notes": {"user_id": str(user.id), "telegram_id": str(user.telegram_id)},
    }
    if user.full_name or user.phone:
        customer: dict[str, str] = {}
        if user.full_name:
            customer["name"] = user.full_name
        if user.phone:
            customer["contact"] = user.phone
        payload["customer"] = customer

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{RAZORPAY_BASE}/payment_links", json=payload, auth=_auth()
            )
        resp.raise_for_status()
        body = resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to create Razorpay payment link")
        raise PaymentError("Could not create payment link") from exc

    payment = Payment(
        user_id=user.id,
        reference_id=reference_id,
        razorpay_link_id=body["id"],
        short_url=body.get("short_url"),
        amount_paise=payload["amount"],
        status="created",
        expires_at=utcnow() + timedelta(seconds=expire_by - int(time.time())),
    )
    db.add(payment)
    await db.flush()
    return payment


def verify_webhook_signature(raw_body: bytes, signature: str) -> bool:
    if not signature or not settings.RAZORPAY_WEBHOOK_SECRET:
        return False
    expected = hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def mark_link_paid(
    db: AsyncSession, link_id: str, payment_id: str, amount_paid_paise: int
) -> tuple[Payment | None, User | None, bool]:
    """Idempotently activates a subscription for a paid payment_link. Returns (payment, user, newly_activated)."""
    payment = (
        await db.execute(
            select(Payment).where(Payment.razorpay_link_id == link_id).with_for_update()
        )
    ).scalar_one_or_none()
    if payment is None:
        logger.warning("Webhook for unknown payment link_id=%s", link_id)
        return None, None, False

    if payment.status == "paid":
        return payment, None, False  # already processed - idempotent no-op

    if amount_paid_paise < payment.amount_paise:
        logger.warning(
            "Partial payment for link_id=%s: paid=%s expected=%s",
            link_id, amount_paid_paise, payment.amount_paise,
        )
        return payment, None, False

    user = (
        await db.execute(select(User).where(User.id == payment.user_id).with_for_update())
    ).scalar_one_or_none()
    if user is None:
        logger.error("Payment %s has no matching user", payment.id)
        return payment, None, False

    subscription_days = await get_setting(db, "subscription_days", 30)
    sub: Subscription = await extend_subscription(
        db, user, int(subscription_days), source="payment"
    )
    # A renewal can be paid from a reminder's link without ever messaging the bot, so the
    # middleware never gets the chance to clear a stale bot_blocked flag - and the digest
    # worker only serves active users.
    reactivate_if_bot_blocked(user)

    payment.status = "paid"
    payment.razorpay_payment_id = payment_id
    payment.paid_at = utcnow()
    payment.subscription_id = sub.id
    await db.flush()
    return payment, user, True


async def sync_payment(db: AsyncSession, payment: Payment) -> Payment:
    """Admin helper: check Razorpay for a pending link's real status and activate if paid."""
    if payment.status != "created" or not payment.razorpay_link_id:
        return payment
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{RAZORPAY_BASE}/payment_links/{payment.razorpay_link_id}", auth=_auth()
            )
        resp.raise_for_status()
        body = resp.json()
    except Exception:  # noqa: BLE001
        logger.exception("Failed to sync payment link %s", payment.razorpay_link_id)
        return payment

    status = body.get("status")
    if status == "paid":
        payments_list = body.get("payments") or []
        payment_id = payments_list[-1]["payment_id"] if payments_list else None
        amount_paid = body.get("amount_paid", payment.amount_paise)
        _, _, _ = await mark_link_paid(
            db, payment.razorpay_link_id, payment_id or "unknown", amount_paid
        )
        await db.refresh(payment)
    elif status in ("expired", "cancelled"):
        payment.status = "expired"
        await db.flush()
    return payment
