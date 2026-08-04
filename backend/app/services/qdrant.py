from typing import Any, List, Optional
import uuid
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as rest_models
from backend.app.config import settings
from backend.app.core.exceptions import VectorDBError
from backend.app.core.logging import logger


class QdrantService:
    """Manages collection management, point indexing, and vector searching in Qdrant."""

    def __init__(self, host: str = settings.QDRANT_HOST, port: int = settings.QDRANT_PORT, in_memory: bool = False):
        if in_memory or host == ":memory:":
            self.client = AsyncQdrantClient(":memory:")
        else:
            self.client = AsyncQdrantClient(
                host=host,
                port=port,
                api_key=settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None,
                timeout=10.0,
            )
        self.collection_name = settings.QDRANT_COLLECTION
        self.dimension = settings.EMBEDDING_DIMENSION

    async def init_collection(self) -> None:
        """Creates the collection if it does not already exist."""
        try:
            collections = await self.client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if self.collection_name not in collection_names:
                await self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=rest_models.VectorParams(
                        size=self.dimension,
                        distance=rest_models.Distance.COSINE,
                    ),
                )
                logger.info("Created Qdrant collection", collection=self.collection_name, size=self.dimension)
        except Exception as e:
            logger.warning("Failed to check/create Qdrant collection, falling back to memory mode", error=str(e))

    async def upsert_points(self, points: List[rest_models.PointStruct]) -> None:
        """Upserts a batch of chunk vectors and payload points into Qdrant."""
        if not points:
            return
        try:
            await self.init_collection()
            await self.client.upsert(
                collection_name=self.collection_name,
                points=points,
            )
        except Exception as e:
            raise VectorDBError(f"Failed to upsert vector points into Qdrant: {str(e)}")

    async def search_points(
        self,
        query_vector: List[float],
        user_id: str,
        limit: int = 5,
        score_threshold: Optional[float] = None,
        document_ids: Optional[List[str]] = None,
        workspace_id: Optional[str] = None,
    ) -> List[rest_models.ScoredPoint]:
        """Executes vector search with strict payload filters."""
        try:
            await self.init_collection()

            must_filters: List[Any] = [
                rest_models.FieldCondition(
                    key="user_id",
                    match=rest_models.MatchValue(value=str(user_id)),
                )
            ]

            if workspace_id:
                must_filters.append(
                    rest_models.FieldCondition(
                        key="workspace_id",
                        match=rest_models.MatchValue(value=str(workspace_id)),
                    )
                )

            if document_ids:
                must_filters.append(
                    rest_models.FieldCondition(
                        key="document_id",
                        match=rest_models.MatchAny(any=[str(doc_id) for doc_id in document_ids]),
                    )
                )

            query_filter = rest_models.Filter(must=must_filters)

            res = await self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=query_filter,
                limit=limit,
                score_threshold=score_threshold,
            )
            return res.points
        except Exception as e:
            raise VectorDBError(f"Failed to perform vector search in Qdrant: {str(e)}")

    async def delete_document_points(self, document_id: str, user_id: str) -> None:
        """Deletes all points matching document_id and user_id."""
        try:
            await self.init_collection()
            filter_condition = rest_models.Filter(
                must=[
                    rest_models.FieldCondition(
                        key="document_id",
                        match=rest_models.MatchValue(value=str(document_id)),
                    ),
                    rest_models.FieldCondition(
                        key="user_id",
                        match=rest_models.MatchValue(value=str(user_id)),
                    ),
                ]
            )
            await self.client.delete(
                collection_name=self.collection_name,
                points_selector=rest_models.FilterSelector(filter=filter_condition),
            )
        except Exception as e:
            raise VectorDBError(f"Failed to delete points for document '{document_id}': {str(e)}")
