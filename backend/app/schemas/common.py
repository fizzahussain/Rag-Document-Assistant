from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check status model."""

    status: str = Field(..., json_schema_extra={"example": "healthy"})
    database: str = Field(..., json_schema_extra={"example": "connected"})
    vector_db: str = Field(..., json_schema_extra={"example": "connected"})


class ErrorResponse(BaseModel):
    """Standardized API error response format."""

    error_code: str = Field(..., json_schema_extra={"example": "VALIDATION_ERROR"})
    message: str = Field(..., json_schema_extra={"example": "File extension not supported."})
    request_id: Optional[str] = Field(None, json_schema_extra={"example": "req_123456789"})
    details: Dict[str, Any] = Field(default_factory=dict)
