"""remove qdrant column

Revision ID: 7b1f5a2c9d10
Revises: 63053c9b55ca
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7b1f5a2c9d10"
down_revision: str | None = "63053c9b55ca"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_document_chunks_qdrant_point_id", table_name="document_chunks")
    op.drop_column("document_chunks", "qdrant_point_id")


def downgrade() -> None:
    op.add_column(
        "document_chunks",
        sa.Column("qdrant_point_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        "ix_document_chunks_qdrant_point_id",
        "document_chunks",
        ["qdrant_point_id"],
    )
