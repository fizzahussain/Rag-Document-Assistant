from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ErrorResponse(BaseModel):
    """Standard API error response"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error_code": "VALIDATION_ERROR",
                "message": "The provided data is invalid",
                "request_id": "9c9f374f-89d8-4db5-b9ca-8b95f47e6137",
                "details": {
                    "field": "file",
                    "reason": "Unsupported file type",
                },
            }
        }
    )

    error_code: str = Field(
        ...,
        min_length=1,
        description="Stable machine-readable error identifier",
        examples=["VALIDATION_ERROR"],
    )
    message: str = Field(
        ...,
        min_length=1,
        description="Safe user-facing error message",
        examples=["The provided data is invalid"],
    )
    request_id: str | None = Field(
        default=None,
        description="Identifier used to trace the request in application logs",
        examples=["9c9f374f-89d8-4db5-b9ca-8b95f47e6137"],
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional structured information about the error",
    )


class ValidationIssue(BaseModel):
    """Validation problem associated with one request field"""

    field: str | None = Field(
        default=None,
        description="Request field associated with the validation error",
        examples=["file"],
    )
    message: str = Field(
        ...,
        min_length=1,
        description="Description of the validation problem",
        examples=["This field is required"],
    )
    error_type: str | None = Field(
        default=None,
        description="Validation error category",
        examples=["missing"],
    )


class RequestValidationErrorResponse(ErrorResponse):
    """Error response for invalid request payloads"""

    validation_errors: list[ValidationIssue] = Field(
        default_factory=list,
        description="Individual validation problems found in the request",
    )


class ServiceHealth(BaseModel):
    """Health information for one application dependency"""

    status: Literal[
        "healthy",
        "unhealthy",
        "degraded",
        "unavailable",
        "not_configured",
    ] = Field(
        ...,
        description="Current service health state",
        examples=["healthy"],
    )
    message: str | None = Field(
        default=None,
        description="Optional safe diagnostic message",
        examples=["Database connection established"],
    )
    latency_ms: float | None = Field(
        default=None,
        ge=0,
        description="Dependency health-check latency in milliseconds",
        examples=[12.4],
    )


class HealthResponse(BaseModel):
    """Application liveness or readiness response"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "service": "rag-document-assistant",
                "version": "1.0.0",
                "request_id": "9c9f374f-89d8-4db5-b9ca-8b95f47e6137",
                "checks": {
                    "database": {
                        "status": "healthy",
                        "message": "Database connection established",
                        "latency_ms": 8.2,
                    },
                    "vector_db": {
                        "status": "healthy",
                        "message": "pgvector extension is available",
                        "latency_ms": 4.1,
                    },
                },
            }
        }
    )

    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        ...,
        description="Overall application health state",
        examples=["healthy"],
    )
    service: str = Field(
        default="rag-document-assistant",
        description="Application service name",
        examples=["rag-document-assistant"],
    )
    version: str | None = Field(
        default=None,
        description="Current application version",
        examples=["1.0.0"],
    )
    request_id: str | None = Field(
        default=None,
        description="Request identifier used for tracing",
        examples=["9c9f374f-89d8-4db5-b9ca-8b95f47e6137"],
    )
    checks: dict[str, ServiceHealth] = Field(
        default_factory=dict,
        description="Health information for application dependencies",
    )


class PaginationMetadata(BaseModel):
    """Pagination information for collection responses"""

    total: int = Field(
        ...,
        ge=0,
        description="Total number of matching records",
        examples=[42],
    )
    limit: int = Field(
        ...,
        ge=1,
        description="Maximum records returned in this response",
        examples=[20],
    )
    offset: int = Field(
        ...,
        ge=0,
        description="Number of records skipped",
        examples=[0],
    )
    has_more: bool = Field(
        ...,
        description="Whether more matching records are available",
        examples=[True],
    )


class MessageResponse(BaseModel):
    """Simple API message response"""

    message: str = Field(
        ...,
        min_length=1,
        description="User-facing confirmation message",
        examples=["Document deleted successfully"],
    )
    request_id: str | None = Field(
        default=None,
        description="Request identifier used for tracing",
        examples=["9c9f374f-89d8-4db5-b9ca-8b95f47e6137"],
    )
