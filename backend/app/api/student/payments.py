"""POST /student/payments/order, POST /student/payments/verify - native Razorpay Checkout SDK
payment flow for the student app. Delegates all activation logic to razorpay_orders.py."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.student.deps import current_student
from app.api.student.schemas import CreateOrderOut, PaymentVerifiedOut, VerifyPaymentIn
from app.config import settings
from app.db.models import Payment, User
from app.db.session import get_db
from app.services.access import access_until
from app.services.payments import PaymentError
from app.services.razorpay_orders import create_order, mark_order_paid, verify_order_signature

router = APIRouter(prefix="/student/payments", tags=["student-payments"])


@router.post("/order", response_model=CreateOrderOut)
async def create_payment_order(
    user: User = Depends(current_student), db: AsyncSession = Depends(get_db)
) -> CreateOrderOut:
    try:
        payment = await create_order(db, user)
    except PaymentError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return CreateOrderOut(
        order_id=payment.razorpay_order_id,
        amount=payment.amount_paise,
        key_id=settings.RAZORPAY_KEY_ID,
    )


@router.post("/verify", response_model=PaymentVerifiedOut)
async def verify_payment(
    payload: VerifyPaymentIn,
    user: User = Depends(current_student),
    db: AsyncSession = Depends(get_db),
) -> PaymentVerifiedOut:
    if not verify_order_signature(
        payload.razorpay_order_id, payload.razorpay_payment_id, payload.razorpay_signature
    ):
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    # Ownership must be checked BEFORE activating - mark_order_paid() has a real side effect
    # (credits a subscription), so it must never run for an order that isn't this student's.
    existing = (
        await db.execute(
            select(Payment).where(Payment.razorpay_order_id == payload.razorpay_order_id)
        )
    ).scalar_one_or_none()
    if existing is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if existing.user_id != user.id:
        raise HTTPException(status_code=403, detail="This order does not belong to you")

    payment, activated_user, _ = await mark_order_paid(
        db, payload.razorpay_order_id, payload.razorpay_payment_id
    )
    subject = activated_user or user
    until = access_until(subject)
    return PaymentVerifiedOut(access_until=until.isoformat() if until else None)
