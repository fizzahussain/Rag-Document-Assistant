from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check status model."""

    status: str = Field(..., example="healthy")
    database: str = Field(..., example="connected")
    vector_db: str = Field(..., example="connected")


class ErrorResponse(BaseModel):
    """Standardized API error response format."""

    error_code: str = Field(..., example="VALIDATION_ERROR")
    message: str = Field(..., example="File extension not supported.")
    request_id: Optional[str] = Field(None, example="req_123456789")
    details: Dict[str, Any] = Field(default_factory=dict)
