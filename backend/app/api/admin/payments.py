"""Payments list, Razorpay sync, CSV export (Chapter 17.5)."""
from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin.deps import owner_only
from app.db.models import Payment, User
from app.db.session import get_db
from app.services.payments import sync_payment

router = APIRouter(prefix="/admin/payments", tags=["admin-payments"])


def _payment_row(payment: Payment, user: User | None) -> dict:
    return {
        "id": payment.id,
        "user_id": payment.user_id,
        "user_name": user.full_name if user else None,
        "user_phone": user.phone if user else None,
        "amount_inr": payment.amount_paise / 100,
        "status": payment.status,
        "razorpay_payment_id": payment.razorpay_payment_id,
        "created_at": payment.created_at.isoformat(),
        "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
    }


async def _query_payments(
    db: AsyncSession, status: Optional[str], date_from: Optional[str], date_to: Optional[str]
) -> list[tuple[Payment, User | None]]:
    stmt = select(Payment)
    if status:
        stmt = stmt.where(Payment.status == status)
    if date_from:
        stmt = stmt.where(Payment.created_at >= datetime.fromisoformat(date_from))
    if date_to:
        stmt = stmt.where(Payment.created_at <= datetime.fromisoformat(date_to))
    stmt = stmt.order_by(Payment.created_at.desc())

    payments = (await db.execute(stmt)).scalars().all()
    user_ids = [p.user_id for p in payments if p.user_id]
    users_by_id: dict[int, User] = {}
    if user_ids:
        rows = (await db.execute(select(User).where(User.id.in_(user_ids)))).scalars().all()
        users_by_id = {u.id: u for u in rows}
    return [(p, users_by_id.get(p.user_id)) for p in payments]


@router.get("")
async def list_payments(
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = 1,
    size: int = 30,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(owner_only),
) -> dict:
    rows = await _query_payments(db, status, date_from, date_to)
    total = len(rows)
    start = (page - 1) * size
    page_rows = rows[start:start + size]
    return {
        "items": [_payment_row(p, u) for p, u in page_rows],
        "total": total, "page": page, "size": size,
    }


@router.post("/{payment_id}/sync")
async def sync_payment_endpoint(
    payment_id: int, db: AsyncSession = Depends(get_db), _admin=Depends(owner_only)
) -> dict:
    payment = await db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    payment = await sync_payment(db, payment)
    return _payment_row(payment, None)


@router.get("/export")
async def export_payments(
    date_from: Optional[str] = None, date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db), _admin=Depends(owner_only),
) -> Response:
    rows = await _query_payments(db, None, date_from, date_to)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "user_name", "user_phone", "amount_inr", "status", "razorpay_payment_id", "created_at", "paid_at"])
    for p, u in rows:
        writer.writerow([
            p.id, u.full_name if u else "", u.phone if u else "",
            p.amount_paise / 100, p.status, p.razorpay_payment_id or "",
            p.created_at.isoformat(), p.paid_at.isoformat() if p.paid_at else "",
        ])

    return Response(
        content=output.getvalue(), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=payments.csv"},
    )
