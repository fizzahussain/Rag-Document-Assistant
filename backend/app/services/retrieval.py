import math
import uuid

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.models.document import Document, DocumentChunk
from backend.app.services.embedder import BaseEmbeddingProvider, EmbeddingProviderFactory


class RetrievedSource(BaseModel):
    document_id: str
    chunk_id: str
    filename: str
    page_number: int | None
    chunk_index: int
    score: float
    text: str


class RetrievalService:
    def __init__(
        self,
        db: AsyncSession,
        embedder: BaseEmbeddingProvider | None = None,
    ) -> None:
        self.db = db
        self.embedder = embedder or EmbeddingProviderFactory.get_provider()

    async def search(
        self,
        query: str,
        user_id: uuid.UUID,
        limit: int = 5,
        score_threshold: float | None = None,
        document_ids: list[uuid.UUID] | None = None,
        workspace_id: str | None = None,
    ) -> list[RetrievedSource]:
        del workspace_id

        if not query.strip():
            return []

        limit = min(max(limit, 1), 50)
        query_vector = await self.embedder.embed_query(query)

        filters = [
            Document.user_id == user_id,
            Document.status == "ready",
            DocumentChunk.embedding.is_not(None),
        ]
        if document_ids:
            filters.append(Document.id.in_(document_ids))

        if settings.DATABASE_URL.startswith("sqlite"):
            return await self._search_in_memory(
                query_vector=query_vector,
                filters=filters,
                limit=limit,
                score_threshold=score_threshold,
            )

        distance = DocumentChunk.embedding.cosine_distance(query_vector)
        result = await self.db.execute(
            select(DocumentChunk, Document, distance.label("distance"))
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(*filters)
            .order_by(distance)
            .limit(limit)
        )

        sources: list[RetrievedSource] = []
        for chunk, document, raw_distance in result.all():
            score = max(0.0, 1.0 - float(raw_distance))
            if score_threshold is not None and score < score_threshold:
                continue
            sources.append(self._to_source(chunk, document, score))

        return sources

    async def _search_in_memory(
        self,
        query_vector: list[float],
        filters: list[object],
        limit: int,
        score_threshold: float | None,
    ) -> list[RetrievedSource]:
        result = await self.db.execute(
            select(DocumentChunk, Document)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(*filters)
        )

        ranked: list[tuple[float, DocumentChunk, Document]] = []
        for chunk, document in result.all():
            score = self._cosine_similarity(query_vector, list(chunk.embedding or []))
            if score_threshold is not None and score < score_threshold:
                continue
            ranked.append((score, chunk, document))

        ranked.sort(key=lambda item: item[0], reverse=True)
        return [
            self._to_source(chunk, document, score)
            for score, chunk, document in ranked[:limit]
        ]

    @staticmethod
    def _cosine_similarity(left: list[float], right: list[float]) -> float:
        if not left or len(left) != len(right):
            return 0.0

        dot_product = sum(a * b for a, b in zip(left, right, strict=True))
        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return dot_product / (left_norm * right_norm)

    @staticmethod
    def _to_source(
        chunk: DocumentChunk,
        document: Document,
        score: float,
    ) -> RetrievedSource:
        return RetrievedSource(
            document_id=str(document.id),
            chunk_id=str(chunk.id),
            filename=document.filename,
            page_number=chunk.page_number,
            chunk_index=chunk.chunk_index,
            score=score,
            text=chunk.text_content,
        )
