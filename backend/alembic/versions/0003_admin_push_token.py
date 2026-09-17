"""admins: expo_push_token, for push notifications to the admin app

Revision ID: 0003
Revises: 0002
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("admins", sa.Column("expo_push_token", sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column("admins", "expo_push_token")
