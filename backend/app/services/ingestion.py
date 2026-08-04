import uuid

from qdrant_client.http import models as rest_models
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.core.exceptions import ExtractionError, NotFoundError, OCRRequiredError
from backend.app.core.logging import logger
from backend.app.models.audit import AuditLog
from backend.app.models.document import Document, DocumentChunk
from backend.app.services.chunker import TextChunker
from backend.app.services.embedder import EmbeddingProviderFactory
from backend.app.services.extractor import ExtractorFactory
from backend.app.services.qdrant import QdrantService, get_qdrant_service
from backend.app.services.storage import StorageService


class IngestionService:
    def __init__(
        self,
        db: AsyncSession,
        storage_service: StorageService | None = None,
        qdrant_service: QdrantService | None = None,
    ) -> None:
        self.db = db
        self.storage = storage_service or StorageService()
        self.qdrant = qdrant_service or get_qdrant_service()
        self.chunker = TextChunker()
        self.embedder = EmbeddingProviderFactory.get_provider()

    async def _audit(
        self,
        document_id: uuid.UUID | None,
        action: str,
        status_value: str,
        error_message: str | None = None,
    ) -> None:
        self.db.add(
            AuditLog(
                document_id=document_id,
                action=action,
                status=status_value,
                error_message=error_message,
            )
        )
        await self.db.commit()

    async def process_document(
        self,
        document_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> Document:
        conditions = [Document.id == document_id]
        if user_id is not None:
            conditions.append(Document.user_id == user_id)
        result = await self.db.execute(select(Document).where(*conditions))
        document = result.scalar_one_or_none()
        if document is None:
            raise NotFoundError("Document not found")

        try:
            document.status = "extracting"
            await self.db.commit()
            file_bytes = await self.storage.read_file(document.storage_path)
            extracted = ExtractorFactory.get_extractor(document.filename).extract(
                file_bytes, document.filename
            )

            document.status = "chunking"
            document.extraction_metadata = extracted.metadata
            await self.db.commit()
            chunks = self.chunker.chunk_document(extracted)
            vectors = await self.embedder.embed_texts([item.text for item in chunks])

            document.status = "indexing"
            await self.db.commit()
            await self.qdrant.delete_document_points(str(document.id), str(document.user_id))
            await self.db.execute(
                delete(DocumentChunk).where(DocumentChunk.document_id == document.id)
            )

            db_chunks: list[DocumentChunk] = []
            points: list[rest_models.PointStruct] = []
            for payload, vector in zip(chunks, vectors, strict=True):
                stable_chunk_id = uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"{document.id}:{payload.chunk_index}:{payload.chunk_hash}",
                )
                db_chunks.append(
                    DocumentChunk(
                        id=stable_chunk_id,
                        document_id=document.id,
                        chunk_index=payload.chunk_index,
                        page_number=payload.page_number,
                        text_content=payload.text,
                        chunk_hash=payload.chunk_hash,
                        qdrant_point_id=stable_chunk_id,
                    )
                )
                points.append(
                    rest_models.PointStruct(
                        id=str(stable_chunk_id),
                        vector=vector,
                        payload={
                            "document_id": str(document.id),
                            "chunk_id": str(stable_chunk_id),
                            "user_id": str(document.user_id),
                            "page_number": payload.page_number,
                            "chunk_index": payload.chunk_index,
                            "filename": document.filename,
                            "file_type": document.mime_type,
                            "embedding_model": settings.EMBEDDING_MODEL,
                            "content_hash": payload.chunk_hash,
                        },
                    )
                )

            self.db.add_all(db_chunks)
            await self.db.commit()
            await self.qdrant.upsert_points(points)
            document.status = "ready"
            await self.db.commit()
            await self.db.refresh(document)
            await self._audit(document.id, "ingest", "success")
            return document
        except OCRRequiredError as exc:
            document.status = "failed"
            await self.db.commit()
            await self._audit(document.id, "ingest", "failed", str(exc))
            raise
        except Exception as exc:
            document.status = "failed"
            await self.db.commit()
            await self._audit(document.id, "ingest", "failed", str(exc))
            logger.exception("Document ingestion failed", document_id=str(document.id))
            raise ExtractionError("Document ingestion failed") from exc

    async def delete_document(self, document_id: uuid.UUID, user_id: uuid.UUID) -> None:
        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.user_id == user_id,
            )
        )
        document = result.scalar_one_or_none()
        if document is None:
            raise NotFoundError("Document not found")
        document.status = "deleting"
        await self.db.commit()
        await self.qdrant.delete_document_points(str(document.id), str(user_id))
        await self.storage.delete_file(document.storage_path)
        await self.db.delete(document)
        await self.db.commit()
        await self._audit(None, "delete", "success")
