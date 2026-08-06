"""add login fields

Revision ID: 8c3a6f2b1d44
Revises: 7b1f5a2c9d10
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8c3a6f2b1d44"
down_revision: str | None = "7b1f5a2c9d10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("name", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("password_hash", sa.String(length=512), nullable=True))
    op.create_index("ix_users_email", "users", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_column("users", "password_hash")
    op.drop_column("users", "name")
