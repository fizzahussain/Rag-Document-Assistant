from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    """Document details response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    filename: str
    storage_path: str
    mime_type: str
    file_hash: str
    file_size: int
    status: str
    extraction_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class DocumentStatusResponse(BaseModel):
    """Document status summary response schema."""

    id: uuid.UUID
    filename: str
    status: str
    file_size: int
    updated_at: datetime


class DocumentChunkResponse(BaseModel):
    """Document chunk response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    page_number: Optional[int] = None
    text_content: str
    chunk_hash: str
    qdrant_point_id: uuid.UUID
