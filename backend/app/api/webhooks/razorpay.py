"""Razorpay webhook: payment_link.paid / expired / cancelled (Chapter 11.2)."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.loader import get_bot
from app.bot.texts import t
from app.db.models import Payment
from app.db.session import get_db
from app.services.payments import mark_link_paid, verify_webhook_signature
from app.services.razorpay_orders import mark_order_paid

logger = logging.getLogger("app.webhooks.razorpay")
router = APIRouter(tags=["webhooks"])


@router.post("/webhooks/razorpay")
async def razorpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_razorpay_signature: str | None = Header(default=None),
) -> Response:
    raw_body = await request.body()

    if not verify_webhook_signature(raw_body, x_razorpay_signature or ""):
        return Response(status_code=400, content="invalid signature")

    payload = await request.json()
    event = payload.get("event", "")
    link_payload = (payload.get("payload", {}) or {}).get("payment_link", {}).get("entity", {})
    link_id = link_payload.get("id")

    # Defense-in-depth for the student app's native Checkout SDK (Orders) flow: the app also
    # verifies the payment client-side via POST /student/payments/verify, and mark_order_paid()
    # is idempotent, so whichever of the two arrives first wins and the other is a safe no-op.
    # A payment_link.paid payment also carries an order_id, but it was never stored on any
    # Payment row (we only set razorpay_order_id for orders our own create_order() made), so
    # this never double-processes a bot/Payment-Links payment. Checked before the link_id-only
    # early return below, since an Orders payment has no payment_link payload at all.
    if event == "payment.captured":
        payment_entity = (payload.get("payload", {}) or {}).get("payment", {}).get("entity", {})
        order_id = payment_entity.get("order_id")
        if order_id:
            try:
                await mark_order_paid(db, order_id, payment_entity.get("id", "unknown"))
                await db.commit()
            except Exception:  # noqa: BLE001
                logger.exception("Error handling Razorpay payment.captured order_id=%s", order_id)
                await db.rollback()
        return Response(status_code=200)

    if not link_id:
        return Response(status_code=200)

    try:
        if event == "payment_link.paid":
            payments_list = link_payload.get("payments") or []
            payment_entity = (payload.get("payload", {}) or {}).get("payment", {}).get("entity", {})
            payment_id = payment_entity.get("id") or (payments_list[-1].get("payment_id") if payments_list else "unknown")
            amount_paid = link_payload.get("amount_paid", payment_entity.get("amount", 0))

            payment, user, newly_activated = await mark_link_paid(
                db, link_id, payment_id, int(amount_paid)
            )
            await db.commit()

            if newly_activated and user is not None:
                await _notify_payment_success(db, user)

        elif event in ("payment_link.expired", "payment_link.cancelled"):
            obj = (
                await db.execute(select(Payment).where(Payment.razorpay_link_id == link_id))
            ).scalar_one_or_none()
            if obj is not None and obj.status == "created":
                obj.status = "expired"
                await db.commit()
    except Exception:  # noqa: BLE001
        logger.exception("Error handling Razorpay webhook event=%s link_id=%s", event, link_id)
        await db.rollback()

    # Defense-in-depth for the student app's native Checkout SDK (Orders) flow: the app also
    # verifies the payment client-side via POST /student/payments/verify, and mark_order_paid()
    # is idempotent, so whichever of the two arrives first wins and the other is a safe no-op.
    # A payment_link.paid payment also carries an order_id, but it was never stored on any
    # Payment row (we only set razorpay_order_id for orders our own create_order() made), so
    # this never double-processes a bot/Payment-Links payment.
    payment_entity = (payload.get("payload", {}) or {}).get("payment", {}).get("entity", {})
    order_id = payment_entity.get("order_id")
    if event == "payment.captured" and order_id:
        try:
            await mark_order_paid(db, order_id, payment_entity.get("id", "unknown"))
            await db.commit()
        except Exception:  # noqa: BLE001
            logger.exception("Error handling Razorpay payment.captured order_id=%s", order_id)
            await db.rollback()

    # Always return 200 once the signature is verified, so Razorpay does not retry forever.
    return Response(status_code=200)


async def _notify_payment_success(db: AsyncSession, user) -> None:
    from app.services.access import subscription_end

    lang = user.language or "mr"
    end = subscription_end(user)
    from app.config import settings

    until = end.astimezone(settings.tz).strftime("%d-%m-%Y") if end else "-"
    try:
        await get_bot().send_message(user.telegram_id, t(lang, "payment_success", until=until))
    except Exception:  # noqa: BLE001
        logger.exception("Failed to send payment_success message to user %s", user.id)
