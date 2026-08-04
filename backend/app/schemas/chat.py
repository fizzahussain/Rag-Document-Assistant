import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.app.services.llm import Citation
from backend.app.services.retrieval import RetrievedSource


class ChatRequest(BaseModel):
    """RAG Chat request payload."""

    user_id: uuid.UUID = Field(..., description="ID of the user sending message")
    conversation_id: uuid.UUID | None = Field(
        default=None, description="Existing conversation ID or None for new session"
    )
    message: str = Field(..., min_length=1, description="User question or query")
    document_ids: list[uuid.UUID] | None = Field(
        default=None, description="Optional document IDs filter"
    )
    top_k: int = Field(
        default=5, ge=1, le=20, description="Top-k context chunks to retrieve"
    )


class ChatResponse(BaseModel):
    """RAG Chat answer payload."""

    conversation_id: uuid.UUID
    message_id: uuid.UUID
    answer: str
    citations: list[Citation]
    retrieved_sources: list[RetrievedSource]
    execution_time_seconds: float


class ConversationResponse(BaseModel):
    """Conversation summary schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    created_at: datetime


class MessageResponse(BaseModel):
    """Message detail schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    retrieved_sources: dict[str, Any] | None = None
    created_at: datetime
