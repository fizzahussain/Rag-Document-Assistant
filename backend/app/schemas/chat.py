import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.app.services.llm import Citation
from backend.app.services.retrieval import RetrievedSource


class ChatRequest(BaseModel):
    conversation_id: uuid.UUID | None = None
    message: str = Field(..., min_length=1, max_length=8000)
    document_ids: list[uuid.UUID] | None = None
    top_k: int = Field(default=5, ge=1, le=20)


class ConversationCreateRequest(BaseModel):
    title: str = Field(default="New Conversation", min_length=1, max_length=255)


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    message_id: uuid.UUID
    answer: str
    citations: list[Citation]
    retrieved_sources: list[RetrievedSource]
    execution_time_seconds: float


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    created_at: datetime


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    retrieved_sources: dict[str, Any] | None = None
    created_at: datetime
