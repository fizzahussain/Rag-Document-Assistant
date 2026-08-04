import uuid
import pytest
from qdrant_client.http import models as rest_models
from backend.app.services.embedder import MockEmbeddingProvider
from backend.app.services.qdrant import QdrantService
from backend.app.services.retrieval import RetrievalService


@pytest.mark.asyncio
async def test_qdrant_in_memory_search():
    # Use in-memory Qdrant client for unit test
    qdrant_service = QdrantService(in_memory=True)
    embedder = MockEmbeddingProvider(dimension=1536)

    user_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    point_id = str(uuid.uuid4())

    text = "PostgreSQL is a powerful open source relational database system."
    vector = await embedder.embed_query(text)

    # Upsert a point
    point = rest_models.PointStruct(
        id=point_id,
        vector=vector,
        payload={
            "document_id": doc_id,
            "chunk_id": point_id,
            "user_id": user_id,
            "page_number": 1,
            "chunk_index": 0,
            "filename": "db.txt",
            "text": text,
        },
    )
    await qdrant_service.upsert_points([point])

    retrieval_service = RetrievalService(qdrant_service=qdrant_service, embedder=embedder)

    # Perform search matching user_id
    results = await retrieval_service.search(
        query="relational database system",
        user_id=user_id,
        limit=5,
    )

    assert len(results) == 1
    assert results[0].filename == "db.txt"
    assert "PostgreSQL" in results[0].text
    assert results[0].score > 0.0

    # Test search with different user_id (user isolation check)
    other_user_id = str(uuid.uuid4())
    empty_results = await retrieval_service.search(
        query="relational database system",
        user_id=other_user_id,
        limit=5,
    )
    assert len(empty_results) == 0
