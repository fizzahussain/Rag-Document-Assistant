from typing import Any

from pydantic import BaseModel

from backend.app.services.embedder import (
    BaseEmbeddingProvider,
    EmbeddingProviderFactory,
)
from backend.app.services.qdrant import QdrantService


class RetrievedSource(BaseModel):
    """Container for retrieved context excerpt and citation information."""

    document_id: str
    chunk_id: str
    filename: str
    page_number: int | None
    chunk_index: int
    score: float
    text: str


class RetrievalService:
    """Orchestrates query embedding, vector search, payload filtering, and deduplication."""

    def __init__(
        self,
        qdrant_service: QdrantService | None = None,
        embedder: BaseEmbeddingProvider | None = None,
    ):
        self.qdrant_service = qdrant_service or QdrantService()
        self.embedder = embedder or EmbeddingProviderFactory.get_provider()

    async def search(
        self,
        query: str,
        user_id: str,
        limit: int = 5,
        score_threshold: float | None = None,
        document_ids: list[str] | None = None,
        workspace_id: str | None = None,
    ) -> list[RetrievedSource]:
        """Performs dense vector retrieval for a query and formats attribution references."""
        if not query.strip():
            return []

        # 1. Generate query embedding vector
        query_vector = await self.embedder.embed_query(query)

        # 2. Search Qdrant vector database with user isolation filters
        scored_points = await self.qdrant_service.search_points(
            query_vector=query_vector,
            user_id=user_id,
            limit=limit * 2,  # Fetch extra for deduplication
            score_threshold=score_threshold,
            document_ids=document_ids,
            workspace_id=workspace_id,
        )

        # 3. Deduplicate results based on text content
        sources: list[RetrievedSource] = []
        seen_texts = set()

        for point in scored_points:
            payload: dict[str, Any] = point.payload or {}
            text_content = payload.get("text", "")

            if text_content in seen_texts:
                continue
            seen_texts.add(text_content)

            sources.append(
                RetrievedSource(
                    document_id=str(payload.get("document_id", "")),
                    chunk_id=str(payload.get("chunk_id", point.id)),
                    filename=payload.get("filename", "unknown"),
                    page_number=payload.get("page_number"),
                    chunk_index=payload.get("chunk_index", 0),
                    score=float(point.score),
                    text=text_content,
                )
            )

            if len(sources) >= limit:
                break

        return sources
