"""add chunk context and document failure details

Revision ID: 9d8f4c1e2a77
Revises: 8c3a6f2b1d44
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9d8f4c1e2a77"
down_revision: str | None = "8c3a6f2b1d44"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("document_chunks", sa.Column("context_summary", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("failure_code", sa.String(length=100), nullable=True))
    op.add_column("documents", sa.Column("failure_message", sa.Text(), nullable=True))
    op.add_column(
        "documents",
        sa.Column("retryable", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("documents", "retryable")
    op.drop_column("documents", "failure_message")
    op.drop_column("documents", "failure_code")
    op.drop_column("document_chunks", "context_summary")
