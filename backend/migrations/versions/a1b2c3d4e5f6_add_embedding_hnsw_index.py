"""add hnsw index on document_chunks.embedding

Revision ID: a1b2c3d4e5f6
Revises: 9d8f4c1e2a77
"""

from collections.abc import Sequence

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "9d8f4c1e2a77"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Approximate nearest-neighbor index for cosine distance searches.
    # Speeds up ORDER BY embedding <=> query as the corpus grows.
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_hnsw
        ON document_chunks
        USING hnsw (embedding vector_cosine_ops)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw")
