"""support_messages: student <-> admin help threads

Revision ID: 0002
Revises: 0001
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "support_messages",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("admin_id", sa.Integer(), nullable=True),
        sa.Column("direction", sa.String(length=3), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["admin_id"], ["admins.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_support_user_created", "support_messages", ["user_id", "created_at"])
    op.create_index("ix_support_direction_created", "support_messages", ["direction", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_support_direction_created", table_name="support_messages")
    op.drop_index("ix_support_user_created", table_name="support_messages")
    op.drop_table("support_messages")
