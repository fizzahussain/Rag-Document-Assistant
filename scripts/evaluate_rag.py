import asyncio
import json
import uuid
from pathlib import Path

from backend.app.database import AsyncSessionLocal
from backend.app.models.document import Document, DocumentChunk
from backend.app.models.user import User
from backend.app.services.chunker import TextChunker
from backend.app.services.embedder import MockEmbeddingProvider
from backend.app.services.extractor import ExtractedDocument, ExtractedPage
from backend.app.services.llm import MockLLMProvider
from backend.app.services.retrieval import RetrievalService


async def run_evaluation() -> None:
    dataset_path = Path(__file__).with_name("eval_dataset.json")
    eval_items = json.loads(dataset_path.read_text(encoding="utf-8"))

    embedder = MockEmbeddingProvider()
    llm = MockLLMProvider()
    user_id = uuid.uuid4()
    document_id = uuid.uuid4()

    sample_text = (
        "PostgreSQL with pgvector stores relational data and vector embeddings "
        "for the RAG application. Scanned image-only PDFs require OCR. "
        "Supported formats include PDF, DOCX, TXT, MD, CSV, HTML, and JSON."
    )
    extracted = ExtractedDocument(
        text=sample_text,
        pages=[ExtractedPage(page_number=1, text=sample_text)],
        metadata={"format": "TXT"},
    )
    chunks = TextChunker(chunk_size=300, chunk_overlap=30).chunk_document(extracted)
    vectors = await embedder.embed_texts([chunk.text for chunk in chunks])

    async with AsyncSessionLocal() as db:
        db.add(User(id=user_id, workspace_id=str(uuid.uuid4())))
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

        for chunk, vector in zip(chunks, vectors, strict=True):
            chunk_id = uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"{document_id}:{chunk.chunk_index}:{chunk.chunk_hash}",
            )
            db.add(
                DocumentChunk(
                    id=chunk_id,
                    document_id=document_id,
                    chunk_index=chunk.chunk_index,
                    page_number=chunk.page_number,
                    text_content=chunk.text,
                    chunk_hash=chunk.chunk_hash,
                    embedding=vector,
                )
            )

        await db.commit()
        retrieval = RetrievalService(db, embedder=embedder)
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

            answer = await llm.generate_answer(query=item["query"], sources=results)
            print(f"Query: {item['query']}")
            print(f"Retrieval hit: {'yes' if hit else 'no'}")
            print(f"Answer: {answer.answer[:150]}")

        hit_rate = (hits / len(eval_items)) * 100
        print(f"Retrieval hit rate: {hit_rate:.1f}%")


if __name__ == "__main__":
    asyncio.run(run_evaluation())
