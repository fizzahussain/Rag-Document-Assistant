import uuid
from typing import List, Optional
from qdrant_client.http import models as rest_models
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.config import settings
from backend.app.core.exceptions import (
    ExtractionError,
    NotFoundError,
    OCRRequiredError,
    ValidationError,
)
from backend.app.core.logging import logger
from backend.app.models.audit import AuditLog
from backend.app.models.document import Document, DocumentChunk
from backend.app.services.chunker import TextChunker
from backend.app.services.embedder import EmbeddingProviderFactory
from backend.app.services.extractor import ExtractorFactory
from backend.app.services.qdrant import QdrantService
from backend.app.services.storage import StorageService


class IngestionService:
    """Orchestrates document ingestion lifecycle, PostgreSQL persistence, and Qdrant indexing."""

    def __init__(
        self,
        db: AsyncSession,
        storage_service: Optional[StorageService] = None,
        qdrant_service: Optional[QdrantService] = None,
    ):
        self.db = db
        self.storage = storage_service or StorageService()
        self.qdrant = qdrant_service or QdrantService()
        self.chunker = TextChunker()
        self.embedder = EmbeddingProviderFactory.get_provider()

    async def log_audit(self, document_id: Optional[uuid.UUID], action: str, status: str, error_message: Optional[str] = None) -> None:
        """Records an audit trail event."""
        log_entry = AuditLog(
            document_id=document_id,
            action=action,
            status=status,
            error_message=error_message,
        )
        self.db.add(log_entry)
        await self.db.commit()

    async def process_document(self, document_id: uuid.UUID) -> Document:
        """Executes the full idempotent ingestion pipeline for a document."""
        # 1. Fetch document
        result = await self.db.execute(select(Document).where(Document.id == document_id))
        doc = result.scalar_one_or_none()
        if not doc:
            raise NotFoundError(f"Document '{document_id}' not found.")

        try:
            # Lifecycle: extracting
            doc.status = "extracting"
            await self.db.commit()

            file_bytes = self.storage.read_file(doc.storage_path)
            extractor = ExtractorFactory.get_extractor(doc.filename)
            extracted_doc = extractor.extract(file_bytes, doc.filename)

            # Lifecycle: extracted
            doc.status = "extracted"
            doc.extraction_metadata = extracted_doc.metadata
            await self.db.commit()

            # Lifecycle: chunking
            doc.status = "chunking"
            await self.db.commit()

            chunk_payloads = self.chunker.chunk_document(extracted_doc)

            # Delete any existing chunks for idempotency on reprocess
            await self.db.execute(
                select(DocumentChunk).where(DocumentChunk.document_id == doc.id)
            )
            await self.qdrant.delete_document_points(str(doc.id), str(doc.user_id))

            # Lifecycle: embedding & indexing
            doc.status = "embedding"
            await self.db.commit()

            chunk_texts = [c.text for c in chunk_payloads]
            embeddings = await self.embedder.embed_texts(chunk_texts)

            doc.status = "indexing"
            await self.db.commit()

            db_chunks: List[DocumentChunk] = []
            qdrant_points: List[rest_models.PointStruct] = []

            for payload, vector in zip(chunk_payloads, embeddings):
                chunk_uuid = payload.chunk_id
                db_chunk = DocumentChunk(
                    id=chunk_uuid,
                    document_id=doc.id,
                    chunk_index=payload.chunk_index,
                    page_number=payload.page_number,
                    text_content=payload.text,
                    chunk_hash=payload.chunk_hash,
                    qdrant_point_id=chunk_uuid,
                )
                db_chunks.append(db_chunk)

                qdrant_points.append(
                    rest_models.PointStruct(
                        id=str(chunk_uuid),
                        vector=vector,
                        payload={
                            "document_id": str(doc.id),
                            "chunk_id": str(chunk_uuid),
                            "user_id": str(doc.user_id),
                            "page_number": payload.page_number,
                            "chunk_index": payload.chunk_index,
                            "filename": doc.filename,
                            "file_type": doc.mime_type,
                            "embedding_model": settings.EMBEDDING_MODEL,
                            "content_hash": payload.chunk_hash,
                            "text": payload.text,
                        },
                    )
                )

            self.db.add_all(db_chunks)
            await self.db.commit()

            # Index to Qdrant
            await self.qdrant.upsert_points(qdrant_points)

            # Lifecycle: ready
            doc.status = "ready"
            await self.db.commit()

            await self.log_audit(doc.id, action="ingest", status="success")
            logger.info("Successfully ingested document", document_id=str(doc.id), filename=doc.filename)
            return doc

        except OCRRequiredError as e:
            doc.status = "failed"
            await self.db.commit()
            await self.log_audit(doc.id, action="ingest", status="failed", error_message=str(e))
            logger.warning("Document requires OCR", document_id=str(doc.id), error=str(e))
            raise

        except Exception as e:
            doc.status = "failed"
            await self.db.commit()
            await self.log_audit(doc.id, action="ingest", status="failed", error_message=str(e))
            logger.error("Failed to ingest document", document_id=str(doc.id), error=str(e))
            raise ExtractionError(f"Ingestion failed for document '{doc.filename}': {str(e)}")

    async def delete_document(self, document_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Deletes document record, chunk records, stored file, and Qdrant points."""
        result = await self.db.execute(
            select(Document).where(Document.id == document_id, Document.user_id == user_id)
        )
        doc = result.scalar_one_or_none()
        if not doc:
            raise NotFoundError(f"Document '{document_id}' not found for this user.")

        doc.status = "deleting"
        await self.db.commit()

        # Delete Qdrant vectors
        await self.qdrant.delete_document_points(str(doc.id), str(user_id))

        # Delete stored file
        self.storage.delete_file(doc.storage_path)

        # Delete database record
        doc.status = "deleted"
        await self.db.delete(doc)
        await self.db.commit()

        await self.log_audit(document_id, action="delete", status="success")
        logger.info("Deleted document and all related records", document_id=str(document_id))
