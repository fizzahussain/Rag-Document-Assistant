import asyncio
import json
import uuid
from pathlib import Path

from qdrant_client.http import models as rest_models

from backend.app.database import AsyncSessionLocal
from backend.app.models.document import Document, DocumentChunk
from backend.app.models.user import User
from backend.app.services.chunker import TextChunker
from backend.app.services.embedder import MockEmbeddingProvider
from backend.app.services.extractor import ExtractedDocument, ExtractedPage
from backend.app.services.llm import MockLLMProvider
from backend.app.services.qdrant import QdrantService
from backend.app.services.retrieval import RetrievalService


async def run_evaluation() -> None:
    dataset_path = Path(__file__).with_name("eval_dataset.json")
    eval_items = json.loads(dataset_path.read_text(encoding="utf-8"))

    qdrant = QdrantService(in_memory=True)
    embedder = MockEmbeddingProvider()
    llm = MockLLMProvider()

    user_id = uuid.uuid4()
    document_id = uuid.uuid4()

    sample_text = (
        "PostgreSQL and Qdrant are the core database systems supported "
        "in the RAG application architecture. "
        "PostgreSQL handles relational data using SQLAlchemy 2.0 async, "
        "while Qdrant stores vectors. "
        "Scanned image-only PDFs require OCR. Supported formats include "
        "PDF, DOCX, TXT, MD, CSV, HTML, and JSON."
    )

    extracted = ExtractedDocument(
        text=sample_text,
        pages=[
            ExtractedPage(
                page_number=1,
                text=sample_text,
            )
        ],
        metadata={"format": "TXT"},
    )

    chunks = TextChunker(
        chunk_size=300,
        chunk_overlap=30,
    ).chunk_document(extracted)

    vectors = await embedder.embed_texts([chunk.text for chunk in chunks])

    async with AsyncSessionLocal() as db:
        db.add(
            User(
                id=user_id,
                workspace_id=str(uuid.uuid4()),
            )
        )

        db.add(
            Document(
                id=document_id,
                user_id=user_id,
                filename="rag_architecture.txt",
                storage_path="evaluation-only",
                mime_type="text/plain",
                file_hash="e" * 64,
                file_size=len(sample_text),
                status="ready",
            )
        )

        points = []

        for chunk, vector in zip(chunks, vectors, strict=True):
            chunk_id = uuid.uuid5(
                uuid.NAMESPACE_URL,
                (f"{document_id}:{chunk.chunk_index}:{chunk.chunk_hash}"),
            )

            db.add(
                DocumentChunk(
                    id=chunk_id,
                    document_id=document_id,
                    chunk_index=chunk.chunk_index,
                    page_number=chunk.page_number,
                    text_content=chunk.text,
                    chunk_hash=chunk.chunk_hash,
                    qdrant_point_id=chunk_id,
                )
            )

            points.append(
                rest_models.PointStruct(
                    id=str(chunk_id),
                    vector=vector,
                    payload={
                        "document_id": str(document_id),
                        "chunk_id": str(chunk_id),
                        "user_id": str(user_id),
                    },
                )
            )

        await db.commit()
        await qdrant.upsert_points(points)

        retrieval = RetrievalService(
            db,
            qdrant_service=qdrant,
            embedder=embedder,
        )

        hits = 0

        for item in eval_items:
            results = await retrieval.search(
                query=item["query"],
                user_id=user_id,
                limit=3,
            )

            retrieved_text = " ".join(result.text for result in results)

            hit = any(
                keyword.lower() in retrieved_text.lower()
                for keyword in item["expected_context_keywords"]
            )

            hits += int(hit)

            answer = await llm.generate_answer(
                query=item["query"],
                sources=results,
            )

            print(f"Query: {item['query']}")
            print(f"Retrieval hit: {'yes' if hit else 'no'}")
            print(f"Answer: {answer.answer[:150]}")

        hit_rate = (hits / len(eval_items)) * 100
        print(f"Retrieval hit rate: {hit_rate:.1f}%")


if __name__ == "__main__":
    asyncio.run(run_evaluation())
