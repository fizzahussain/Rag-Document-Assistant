import uuid

import pytest

from backend.app.config import settings
from backend.app.database import AsyncSessionLocal
from backend.app.models.document import Document, DocumentChunk
from backend.app.models.user import User
from backend.app.services.embedder import MockEmbeddingProvider
from backend.app.services.retrieval import RetrievalService


@pytest.mark.asyncio
async def test_pgvector_search_returns_owned_database_chunks() -> None:
    embedder = MockEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)
    user_id = uuid.uuid4()
    document_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    text = "PostgreSQL is a powerful open source relational database system."
    vector = await embedder.embed_query(text)

    async with AsyncSessionLocal() as db:
        db.add(User(id=user_id, workspace_id=str(uuid.uuid4())))
        db.add(
            Document(
                id=document_id,
                user_id=user_id,
                filename="db.txt",
                storage_path="unused",
                mime_type="text/plain",
                file_hash="a" * 64,
                file_size=len(text),
                status="ready",
            )
        )
        db.add(
            DocumentChunk(
                id=chunk_id,
                document_id=document_id,
                chunk_index=0,
                page_number=1,
                text_content=text,
                chunk_hash="b" * 64,
                embedding=vector,
            )
        )
        await db.commit()

        retrieval = RetrievalService(db, embedder=embedder)
        results = await retrieval.search(
            query="relational database system",
            user_id=user_id,
            limit=5,
        )
        assert len(results) == 1
        assert results[0].text == text

        other_results = await retrieval.search(
            query="relational database system",
            user_id=uuid.uuid4(),
            limit=5,
        )
        assert other_results == []
