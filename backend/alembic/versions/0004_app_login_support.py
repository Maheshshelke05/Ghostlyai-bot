"""users: nullable telegram_id (app-only signups have no Telegram history), unique phone,
expo_push_token for push notifications to the student app

Revision ID: 0004
Revises: 0003
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("users", "telegram_id", existing_type=sa.BigInteger(), nullable=True)

    # Defensive dedup before the unique constraint: every phone was entered by its own Telegram
    # user today so this should be a no-op, but a legacy collision would otherwise abort the
    # migration outright. Keep the earliest-created row's phone per value, blank the rest.
    op.execute(
        """
        UPDATE users SET phone = NULL
        WHERE phone IS NOT NULL AND id NOT IN (
            SELECT DISTINCT ON (phone) id FROM users
            WHERE phone IS NOT NULL
            ORDER BY phone, created_at ASC
        )
        """
    )
    op.drop_index("ix_users_phone", table_name="users")
    op.create_unique_constraint("uq_users_phone", "users", ["phone"])

    op.add_column("users", sa.Column("expo_push_token", sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "expo_push_token")
    op.drop_constraint("uq_users_phone", "users", type_="unique")
    op.create_index("ix_users_phone", "users", ["phone"])
    op.alter_column("users", "telegram_id", existing_type=sa.BigInteger(), nullable=False)
