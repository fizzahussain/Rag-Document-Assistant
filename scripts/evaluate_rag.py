import asyncio
import json
import os
import uuid
from backend.app.services.chunker import TextChunker
from backend.app.services.embedder import MockEmbeddingProvider
from backend.app.services.extractor import ExtractedDocument, ExtractedPage
from backend.app.services.llm import MockLLMProvider
from backend.app.services.qdrant import QdrantService
from backend.app.services.retrieval import RetrievalService, RetrievedSource


async def run_evaluation():
    print("--- Starting RAG Retrieval and Quality Evaluation ---")

    dataset_path = os.path.join(os.path.dirname(__file__), "eval_dataset.json")
    with open(dataset_path, "r") as f:
        eval_items = json.load(f)

    # Initialize in-memory evaluation index
    qdrant = QdrantService(in_memory=True)
    embedder = MockEmbeddingProvider()
    llm = MockLLMProvider()
    retrieval = RetrievalService(qdrant_service=qdrant, embedder=embedder)

    user_id = str(uuid.uuid4())

    # Ingest synthetic evaluation document
    sample_text = (
        "PostgreSQL and Qdrant are the core database systems supported in the RAG application architecture. "
        "PostgreSQL handles relational data using SQLAlchemy 2.0 async, while Qdrant stores vectors. "
        "When scanned image-only PDFs are ingested, the system detects little or no extractable text and returns an OCR required error status. "
        "The file formats supported for document extraction are PDF, DOCX, TXT, MD, CSV, HTML, and JSON."
    )

    doc = ExtractedDocument(
        text=sample_text,
        pages=[ExtractedPage(page_number=1, text=sample_text)],
        metadata={"format": "TXT"},
    )

    chunker = TextChunker(chunk_size=300, chunk_overlap=30)
    chunks = chunker.chunk_document(doc)
    
    texts = [c.text for c in chunks]
    vectors = await embedder.embed_texts(texts)

    from qdrant_client.http import models as rest_models
    points = []
    for c, v in zip(chunks, vectors):
        points.append(
            rest_models.PointStruct(
                id=str(c.chunk_id),
                vector=v,
                payload={
                    "document_id": str(uuid.uuid4()),
                    "chunk_id": str(c.chunk_id),
                    "user_id": user_id,
                    "page_number": c.page_number,
                    "chunk_index": c.chunk_index,
                    "filename": "rag_architecture.txt",
                    "text": c.text,
                },
            )
        )
    await qdrant.upsert_points(points)

    hits = 0
    total_evals = len(eval_items)

    for item in eval_items:
        query = item["query"]
        expected_keywords = item["expected_context_keywords"]

        results = await retrieval.search(query=query, user_id=user_id, limit=3)
        retrieved_texts = " ".join(r.text for r in results)

        hit = any(kw.lower() in retrieved_texts.lower() for kw in expected_keywords)
        if hit:
            hits += 1

        answer_obj = await llm.generate_answer(query=query, sources=results)
        print(f"\nQuery: {query}")
        print(f"Retrieval Hit: {'YES' if hit else 'NO'}")
        print(f"Answer: {answer_obj.answer[:150]}...")
        print(f"Citations Count: {len(answer_obj.citations)}")

    hit_rate = (hits / total_evals) * 100
    print(f"\n--- Final Metric Summary ---")
    print(f"Total Queries Evaluated: {total_evals}")
    print(f"Retrieval Hit Rate: {hit_rate:.1f}%")
    print("---------------------------------------------")


if __name__ == "__main__":
    asyncio.run(run_evaluation())
