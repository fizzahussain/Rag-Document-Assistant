import uuid
import pytest
from backend.app.services.chunker import TextChunker
from backend.app.services.embedder import MockEmbeddingProvider
from backend.app.services.extractor import ExtractedDocument, ExtractedPage
from backend.app.services.llm import MockLLMProvider
from backend.app.services.qdrant import QdrantService
from backend.app.services.retrieval import RetrievalService
from qdrant_client.http import models as rest_models


@pytest.mark.asyncio
async def test_end_to_end_rag_flow():
    # 1. Initialize services in memory
    qdrant = QdrantService(in_memory=True)
    embedder = MockEmbeddingProvider()
    llm = MockLLMProvider()
    retrieval = RetrievalService(qdrant_service=qdrant, embedder=embedder)

    user_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())

    # 2. Extract & Chunk Document
    doc_text = "FastAPI is a modern, fast web framework for building APIs with Python 3.8+ based on standard Python type hints."
    extracted_doc = ExtractedDocument(
        text=doc_text,
        pages=[ExtractedPage(page_number=1, text=doc_text)],
        metadata={"format": "TXT"},
    )
    chunker = TextChunker()
    chunks = chunker.chunk_document(extracted_doc)

    assert len(chunks) > 0

    # 3. Embed & Index to Qdrant
    vectors = await embedder.embed_texts([c.text for c in chunks])
    points = []
    for c, v in zip(chunks, vectors):
        points.append(
            rest_models.PointStruct(
                id=str(c.chunk_id),
                vector=v,
                payload={
                    "document_id": doc_id,
                    "chunk_id": str(c.chunk_id),
                    "user_id": user_id,
                    "page_number": c.page_number,
                    "chunk_index": c.chunk_index,
                    "filename": "fastapi_overview.txt",
                    "text": c.text,
                },
            )
        )
    await qdrant.upsert_points(points)

    # 4. Perform Retrieval Search
    results = await retrieval.search(query="What is FastAPI?", user_id=user_id, limit=3)
    assert len(results) == 1
    assert results[0].filename == "fastapi_overview.txt"
    assert "web framework" in results[0].text

    # 5. Generate RAG Answer
    answer_obj = await llm.generate_answer(query="What is FastAPI?", sources=results)
    assert "FastAPI" in answer_obj.answer
    assert len(answer_obj.citations) == 1
    assert answer_obj.citations[0].filename == "fastapi_overview.txt"

    # 6. Delete Document Vectors & Verify Clean Purge
    await qdrant.delete_document_points(doc_id, user_id)
    cleared_results = await retrieval.search(query="What is FastAPI?", user_id=user_id, limit=3)
    assert len(cleared_results) == 0
