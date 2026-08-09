import hashlib
import uuid

import anyio
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
from backend.app.services.llm import LLMProviderFactory
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
        self.llm = LLMProviderFactory.get_provider()

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
        document.failure_message = message[:1000]
        document.retryable = retryable
        await self.db.commit()
        await self._audit(document.id, "ingest", "failed", message[:1000])

    @staticmethod
    def _stored_chunk_hash(document_id: uuid.UUID, payload) -> str:
        raw = (
            f"{document_id}:{payload.chunk_index}:{payload.page_number}:"
            f"{payload.chunk_hash}"
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

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
            extractor = ExtractorFactory.get_extractor(document.filename)
            extracted = await anyio.to_thread.run_sync(
                extractor.extract,
                file_bytes,
                document.filename,
            )

            document.status = "chunking"
            document.extraction_metadata = extracted.metadata
            await self.db.commit()

            chunks = await anyio.to_thread.run_sync(
                self.chunker.chunk_document,
                extracted,
            )
            if not chunks:
                raise ExtractionError("No searchable chunks could be created from the document")

            if self.chunker.context_summary_enabled:
                semantic_summary = ""
                rolling_summary = ""
                pending_chunks: list[str] = []
                stride = max(32, settings.CHUNK_CONTEXT_LLM_STRIDE)

                for chunk in chunks:
                    chunk.context_summary = rolling_summary or None
                    rolling_summary = self.chunker._update_rolling_summary(
                        rolling_summary,
                        chunk.text,
                    )
                    pending_chunks.append(chunk.text)

                    if len(pending_chunks) >= stride:
                        semantic_summary = await self.llm.summarize_context(
                            semantic_summary,
                            "\n\n".join(pending_chunks),
                            self.chunker.context_summary_max_chars,
                        )
                        rolling_summary = semantic_summary or rolling_summary
                        pending_chunks.clear()

            document.status = "embedding"
            await self.db.commit()

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
                stored_hash = self._stored_chunk_hash(document.id, payload)
                stable_chunk_id = uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"{document.id}:{payload.chunk_index}:{stored_hash}",
                )
                db_chunks.append(
                    DocumentChunk(
                        id=stable_chunk_id,
                        document_id=document.id,
                        chunk_index=payload.chunk_index,
                        page_number=payload.page_number,
                        text_content=payload.text,
                        context_summary=payload.context_summary,
                        chunk_hash=stored_hash,
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
            safe_message = "The document could not be indexed. Retry the document."
            await self._mark_failed(
                document,
                code="processing_failed",
                message=safe_message,
                retryable=True,
            )
            logger.exception(
                "Document ingestion failed",
                document_id=str(document.id),
                error_type=exc.__class__.__name__,
            )
            raise ExtractionError(safe_message) from exc

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
        document.failure_code = None
        document.failure_message = None
        document.retryable = False
        await self.db.commit()

        try:
            await self.storage.delete_file(document.storage_path)
        except Exception as exc:
            logger.warning(
                "Stored file could not be deleted; removing database record",
                document_id=str(document_id),
                storage_path=document.storage_path,
                error_type=exc.__class__.__name__,
            )

        try:
            await self.db.delete(document)
            await self.db.commit()
            await self._audit(None, "delete", "success")
        except Exception:
            await self.db.rollback()
            logger.exception("Document deletion failed", document_id=str(document_id))
            raise
