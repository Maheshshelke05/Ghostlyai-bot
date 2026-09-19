"""payments: razorpay_order_id, for the student app's native Razorpay Checkout flow
(separate from the bot's existing Payment-Links flow, which keeps using razorpay_link_id)

Revision ID: 0005
Revises: 0004
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("payments", sa.Column("razorpay_order_id", sa.String(length=64), nullable=True))
    op.create_unique_constraint("uq_payments_razorpay_order_id", "payments", ["razorpay_order_id"])


def downgrade() -> None:
    op.drop_constraint("uq_payments_razorpay_order_id", "payments", type_="unique")
    op.drop_column("payments", "razorpay_order_id")
