"""T23-T26: Razorpay signature verification and idempotent payment activation (Chapter 21.1)."""
import hashlib
import hmac
from datetime import timedelta

import pytest

from app.config import settings
from app.db.models import Payment, utcnow
from app.services.payments import get_or_create_payment_link, mark_link_paid, verify_webhook_signature

from tests.conftest import make_user


def test_verify_webhook_signature_valid_and_tampered(monkeypatch):
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", "test-secret")
    body = b'{"event":"payment_link.paid"}'
    good_sig = hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()

    assert verify_webhook_signature(body, good_sig) is True
    assert verify_webhook_signature(body, "0" * 64) is False
    assert verify_webhook_signature(body, "") is False


async def test_mark_link_paid_twice_only_activates_once(db):
    user = await make_user(db)
    payment = Payment(
        user_id=user.id, reference_id="u1_abc123", razorpay_link_id="plink_test1",
        amount_paise=9900, status="created", expires_at=utcnow() + timedelta(hours=1),
    )
    db.add(payment)
    await db.flush()

    _, activated_user, newly_activated_1 = await mark_link_paid(db, "plink_test1", "pay_1", 9900)
    assert newly_activated_1 is True
    assert activated_user is not None

    _, _, newly_activated_2 = await mark_link_paid(db, "plink_test1", "pay_1", 9900)
    assert newly_activated_2 is False


async def test_mark_link_paid_partial_amount_does_not_activate(db):
    user = await make_user(db)
    payment = Payment(
        user_id=user.id, reference_id="u2_def456", razorpay_link_id="plink_test2",
        amount_paise=9900, status="created", expires_at=utcnow() + timedelta(hours=1),
    )
    db.add(payment)
    await db.flush()

    _, activated_user, newly_activated = await mark_link_paid(db, "plink_test2", "pay_2", 5000)
    assert newly_activated is False
    assert activated_user is None
    assert payment.status == "created"


async def test_payment_link_reuse_when_valid(db, monkeypatch):
    user = await make_user(db)
    existing = Payment(
        user_id=user.id, reference_id="u3_ghi789", razorpay_link_id="plink_existing",
        short_url="https://rzp.io/i/existing", amount_paise=9900, status="created",
        expires_at=utcnow() + timedelta(hours=2),
    )
    db.add(existing)
    await db.flush()

    def _boom(*args, **kwargs):
        raise AssertionError("Should not call Razorpay when a valid link can be reused")

    monkeypatch.setattr("app.services.payments.httpx.AsyncClient", _boom)

    result = await get_or_create_payment_link(db, user)
    assert result.id == existing.id
    assert result.razorpay_link_id == "plink_existing"
