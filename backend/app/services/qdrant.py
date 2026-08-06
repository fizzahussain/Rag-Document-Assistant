from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as rest_models

from backend.app.config import settings
from backend.app.core.exceptions import VectorDBError


class QdrantService:
    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        *,
        in_memory: bool = False,
    ) -> None:
        resolved_host = host or settings.QDRANT_HOST
        resolved_port = port or settings.QDRANT_PORT
        api_key = settings.QDRANT_API_KEY.get_secret_value() if settings.QDRANT_API_KEY else None
        if in_memory or resolved_host == ":memory:":
            self.client = AsyncQdrantClient(location=":memory:")
        else:
            self.client = AsyncQdrantClient(
                host=resolved_host,
                port=resolved_port,
                api_key=api_key,
                timeout=settings.QDRANT_TIMEOUT_SECONDS,
            )
        self.collection_name = settings.QDRANT_COLLECTION
        self.dimension = settings.EMBEDDING_DIMENSION

    async def close(self) -> None:
        await self.client.close()

    async def init_collection(self) -> None:
        try:
            if not await self.client.collection_exists(self.collection_name):
                await self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=rest_models.VectorParams(
                        size=self.dimension,
                        distance=rest_models.Distance.COSINE,
                    ),
                )
                await self._create_payload_indexes()
                return

            info = await self.client.get_collection(self.collection_name)
            vectors = info.config.params.vectors
            if isinstance(vectors, rest_models.VectorParams) and vectors.size != self.dimension:
                raise VectorDBError(
                    f"Qdrant dimension mismatch: expected {self.dimension}, found {vectors.size}"
                )
        except VectorDBError:
            raise
        except Exception as exc:
            raise VectorDBError("Qdrant collection initialization failed") from exc

    async def _create_payload_indexes(self) -> None:
        for field_name in ("user_id", "document_id", "workspace_id"):
            try:
                await self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field_name,
                    field_schema=rest_models.PayloadSchemaType.KEYWORD,
                )
            except Exception:
                # Local in-memory Qdrant may not support persistent payload indexes
                continue

    async def upsert_points(self, points: list[rest_models.PointStruct]) -> None:
        if not points:
            return
        await self.init_collection()
        try:
            await self.client.upsert(
                collection_name=self.collection_name,
                points=points,
                wait=True,
            )
        except Exception as exc:
            raise VectorDBError("Failed to index vector points") from exc

    async def search_points(
        self,
        query_vector: list[float],
        user_id: str,
        limit: int = 5,
        score_threshold: float | None = None,
        document_ids: list[str] | None = None,
        workspace_id: str | None = None,
    ) -> list[rest_models.ScoredPoint]:
        if not user_id:
            raise VectorDBError("A user filter is required for vector search")
        await self.init_collection()
        must_filters: list[Any] = [
            rest_models.FieldCondition(
                key="user_id",
                match=rest_models.MatchValue(value=user_id),
            )
        ]
        if document_ids:
            must_filters.append(
                rest_models.FieldCondition(
                    key="document_id",
                    match=rest_models.MatchAny(any=document_ids),
                )
            )
        if workspace_id:
            must_filters.append(
                rest_models.FieldCondition(
                    key="workspace_id",
                    match=rest_models.MatchValue(value=workspace_id),
                )
            )
        try:
            response = await self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=rest_models.Filter(must=must_filters),
                limit=min(max(limit, 1), 100),
                score_threshold=score_threshold,
                with_payload=True,
            )
            return list(response.points)
        except Exception as exc:
            raise VectorDBError("Failed to perform vector search") from exc

    async def delete_document_points(self, document_id: str, user_id: str) -> None:
        await self.init_collection()
        selector = rest_models.FilterSelector(
            filter=rest_models.Filter(
                must=[
                    rest_models.FieldCondition(
                        key="document_id",
                        match=rest_models.MatchValue(value=document_id),
                    ),
                    rest_models.FieldCondition(
                        key="user_id",
                        match=rest_models.MatchValue(value=user_id),
                    ),
                ]
            )
        )
        try:
            await self.client.delete(
                collection_name=self.collection_name,
                points_selector=selector,
                wait=True,
            )
        except Exception as exc:
            raise VectorDBError("Failed to delete document vectors") from exc


_shared_qdrant_service: QdrantService | None = None


def get_qdrant_service() -> QdrantService:
    global _shared_qdrant_service
    if _shared_qdrant_service is None:
        _shared_qdrant_service = QdrantService()
    return _shared_qdrant_service


async def close_qdrant_service() -> None:
    global _shared_qdrant_service
    if _shared_qdrant_service is not None:
        await _shared_qdrant_service.close()
        _shared_qdrant_service = None
