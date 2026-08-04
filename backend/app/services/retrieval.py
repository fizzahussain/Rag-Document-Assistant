import uuid

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.document import Document, DocumentChunk
from backend.app.services.embedder import BaseEmbeddingProvider, EmbeddingProviderFactory
from backend.app.services.qdrant import QdrantService, get_qdrant_service


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
        qdrant_service: QdrantService | None = None,
        embedder: BaseEmbeddingProvider | None = None,
    ) -> None:
        self.db = db
        self.qdrant_service = qdrant_service or get_qdrant_service()
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
        if not query.strip():
            return []
        limit = min(max(limit, 1), 50)

        if document_ids:
            owned = await self.db.execute(
                select(Document.id).where(
                    Document.user_id == user_id,
                    Document.id.in_(document_ids),
                )
            )
            owned_ids = set(owned.scalars().all())
            if owned_ids != set(document_ids):
                return []

        query_vector = await self.embedder.embed_query(query)
        points = await self.qdrant_service.search_points(
            query_vector=query_vector,
            user_id=str(user_id),
            limit=limit * 2,
            score_threshold=score_threshold,
            document_ids=[str(item) for item in document_ids] if document_ids else None,
            workspace_id=workspace_id,
        )
        if not points:
            return []

        score_by_chunk: dict[uuid.UUID, float] = {}
        for point in points:
            payload = point.payload or {}
            raw_chunk_id = payload.get("chunk_id", point.id)
            try:
                score_by_chunk[uuid.UUID(str(raw_chunk_id))] = float(point.score)
            except (ValueError, TypeError):
                continue

        if not score_by_chunk:
            return []

        result = await self.db.execute(
            select(DocumentChunk, Document)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(
                DocumentChunk.id.in_(list(score_by_chunk)),
                Document.user_id == user_id,
                Document.status == "ready",
            )
        )
        rows = result.all()
        sources = [
            RetrievedSource(
                document_id=str(document.id),
                chunk_id=str(chunk.id),
                filename=document.filename,
                page_number=chunk.page_number,
                chunk_index=chunk.chunk_index,
                score=score_by_chunk[chunk.id],
                text=chunk.text_content,
            )
            for chunk, document in rows
        ]
        sources.sort(key=lambda item: item.score, reverse=True)
        return sources[:limit]
