import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    filename: str
    mime_type: str
    file_size: int
    status: str
    extraction_metadata: dict[str, Any] | None = None
    failure_code: str | None = None
    failure_message: str | None = None
    retryable: bool = False
    created_at: datetime
    updated_at: datetime


class DocumentStatusResponse(BaseModel):
    id: uuid.UUID
    filename: str
    status: str
    file_size: int
    updated_at: datetime
    failure_code: str | None = None
    failure_message: str | None = None
    retryable: bool = False


class DocumentChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    page_number: int | None = None
    text_content: str
    context_summary: str | None = None
    chunk_hash: str


class DocumentPreviewPage(BaseModel):
    page_number: int
    text: str


class DocumentPreviewResponse(BaseModel):
    id: uuid.UUID
    filename: str
    mime_type: str
    pages: list[DocumentPreviewPage]
    metadata: dict[str, Any] | None = None
