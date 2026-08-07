import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import ExtractionError, NotFoundError, OCRRequiredError
from backend.app.core.logging import logger
from backend.app.models.audit import AuditLog
from backend.app.models.document import Document, DocumentChunk
from backend.app.services.chunker import TextChunker
from backend.app.services.embedder import EmbeddingProviderFactory
from backend.app.services.extractor import ExtractorFactory
from backend.app.services.storage import StorageService


class IngestionService:
    def __init__(
        self,
        db: AsyncSession,
        storage_service: StorageService | None = None,
    ) -> None:
        self.db = db
        self.storage = storage_service or StorageService()
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

    async def _mark_failed(
        self,
        document: Document,
        code: str,
        message: str,
        retryable: bool,
    ) -> None:
        await self.db.rollback()
        document.status = "failed"
        document.failure_code = code
        document.failure_message = message[:4000]
        document.retryable = retryable
        await self.db.commit()
        await self._audit(document.id, "ingest", "failed", message)

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
            document.failure_code = None
            document.failure_message = None
            document.retryable = False
            document.status = "extracting"
            await self.db.commit()

            file_bytes = await self.storage.read_file(document.storage_path)
            extracted = ExtractorFactory.get_extractor(document.filename).extract(
                file_bytes,
                document.filename,
            )

            document.status = "chunking"
            document.extraction_metadata = extracted.metadata
            await self.db.commit()

            chunks = self.chunker.chunk_document(extracted)
            if not chunks:
                raise ExtractionError("No searchable chunks could be created from the document")

            embedding_inputs = [self.chunker.embedding_text(item) for item in chunks]
            vectors = await self.embedder.embed_texts(embedding_inputs)

            document.status = "indexing"
            await self.db.commit()

            await self.db.execute(
                delete(DocumentChunk).where(DocumentChunk.document_id == document.id)
            )
            await self.db.flush()

            db_chunks: list[DocumentChunk] = []
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
                        context_summary=payload.context_summary,
                        chunk_hash=payload.chunk_hash,
                        embedding=vector,
                    )
                )

            self.db.add_all(db_chunks)
            document.status = "ready"
            document.failure_code = None
            document.failure_message = None
            document.retryable = False
            await self.db.commit()
            await self.db.refresh(document)
            await self._audit(document.id, "ingest", "success")
            return document

        except OCRRequiredError as exc:
            await self._mark_failed(
                document,
                code="ocr_required",
                message=str(exc),
                retryable=True,
            )
            raise
        except Exception as exc:
            message = str(exc) or exc.__class__.__name__
            await self._mark_failed(
                document,
                code="processing_failed",
                message=message,
                retryable=True,
            )
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

        previous_status = document.status if document.status != "deleting" else "failed"
        document.status = "deleting"
        document.failure_code = None
        document.failure_message = None
        document.retryable = False
        await self.db.commit()

        try:
            await self.storage.delete_file(document.storage_path)
            await self.db.delete(document)
            await self.db.commit()
            await self._audit(None, "delete", "success")
        except Exception as exc:
            await self.db.rollback()
            result = await self.db.execute(
                select(Document).where(
                    Document.id == document_id,
                    Document.user_id == user_id,
                )
            )
            existing = result.scalar_one_or_none()
            if existing is not None:
                existing.status = previous_status
                existing.failure_code = "delete_failed"
                existing.failure_message = str(exc)[:4000]
                existing.retryable = True
                await self.db.commit()
            logger.exception("Document deletion failed", document_id=str(document_id))
            raise
