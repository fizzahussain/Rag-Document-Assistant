import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from backend.app.api.router import api_router
from backend.app.config import settings
from backend.app.core.exceptions import RAGException
from backend.app.core.logging import logger, setup_logging
from backend.app.database import close_database

setup_logging()


ERROR_STATUS_CODES = {
    "AUTHENTICATION_ERROR": status.HTTP_401_UNAUTHORIZED,
    "AUTHORIZATION_ERROR": status.HTTP_403_FORBIDDEN,
    "NOT_FOUND": status.HTTP_404_NOT_FOUND,
    "CONFLICT_ERROR": status.HTTP_409_CONFLICT,
    "DUPLICATE_DOCUMENT": status.HTTP_409_CONFLICT,
    "FILE_TOO_LARGE": status.HTTP_413_CONTENT_TOO_LARGE,
    "UNSUPPORTED_FILE_TYPE": status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    "VALIDATION_ERROR": status.HTTP_422_UNPROCESSABLE_CONTENT,
    "OCR_REQUIRED": status.HTTP_422_UNPROCESSABLE_CONTENT,
    "RATE_LIMIT_EXCEEDED": status.HTTP_429_TOO_MANY_REQUESTS,
    "STORAGE_ERROR": status.HTTP_503_SERVICE_UNAVAILABLE,
    "VECTOR_DB_ERROR": status.HTTP_503_SERVICE_UNAVAILABLE,
    "DATABASE_ERROR": status.HTTP_503_SERVICE_UNAVAILABLE,
    "SERVICE_UNAVAILABLE": status.HTTP_503_SERVICE_UNAVAILABLE,
    "LLM_SERVICE_ERROR": status.HTTP_503_SERVICE_UNAVAILABLE,
    "EMBEDDING_ERROR": status.HTTP_503_SERVICE_UNAVAILABLE,
    "RETRIEVAL_ERROR": status.HTTP_503_SERVICE_UNAVAILABLE,
    "EXTRACTION_ERROR": status.HTTP_422_UNPROCESSABLE_CONTENT,
    "PROCESSING_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
}


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown"""

    logger.info("Application starting")

    try:
        yield
    finally:
        logger.info("Application shutting down")
        await close_database()


app = FastAPI(
    title="Multi-User RAG API",
    description=("Secure file ingestion, semantic retrieval, and grounded question answering"),
    version="1.0.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.ALLOWED_ORIGINS),
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS",
    ],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Request-ID",
    ],
    expose_headers=[
        "X-Request-ID",
        "X-Process-Time-MS",
    ],
)


def get_request_id(request: Request) -> str:
    """Return the current request ID"""

    return getattr(
        request.state,
        "request_id",
        "unknown",
    )


def build_error_response(
    *,
    status_code: int,
    error_code: str,
    message: str,
    request_id: str,
    details: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Build a standardized API error response"""

    response_headers = {
        "X-Request-ID": request_id,
        **(headers or {}),
    }

    return JSONResponse(
        status_code=status_code,
        headers=response_headers,
        content={
            "error_code": error_code,
            "message": message,
            "request_id": request_id,
            "details": details or {},
        },
    )


@app.middleware("http")
async def add_request_context(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    """Attach request IDs and timing information"""

    incoming_request_id = request.headers.get(
        "X-Request-ID",
        "",
    ).strip()

    request_id = incoming_request_id[:128] if incoming_request_id else str(uuid.uuid4())

    request.state.request_id = request_id
    started_at = time.perf_counter()

    response = await call_next(request)

    duration_ms = (time.perf_counter() - started_at) * 1000

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-MS"] = f"{duration_ms:.2f}"

    logger.info(
        "Request completed",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round(duration_ms, 2),
    )

    return response


@app.exception_handler(RAGException)
async def rag_exception_handler(
    request: Request,
    exc: RAGException,
) -> JSONResponse:
    """Convert application exceptions into API responses"""

    request_id = get_request_id(request)

    status_code = ERROR_STATUS_CODES.get(
        exc.error_code,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

    log_method = (
        logger.error if status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR else logger.warning
    )

    log_method(
        "Application exception",
        error_code=exc.error_code,
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status_code=status_code,
    )

    headers: dict[str, str] = {}

    if exc.error_code == "AUTHENTICATION_ERROR":
        headers["WWW-Authenticate"] = "Bearer"

    if exc.error_code == "RATE_LIMIT_EXCEEDED":
        retry_after = exc.details.get("retry_after")

        if retry_after is not None:
            headers["Retry-After"] = str(retry_after)

    return build_error_response(
        status_code=status_code,
        error_code=exc.error_code,
        message=exc.message,
        request_id=request_id,
        details=exc.details,
        headers=headers,
    )


@app.exception_handler(RequestValidationError)
async def request_validation_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return a consistent response for invalid request data"""

    request_id = get_request_id(request)
    validation_errors: list[dict[str, str | None]] = []

    for error in exc.errors():
        location = error.get("loc", ())

        field = ".".join(
            str(item)
            for item in location
            if item
            not in {
                "body",
                "query",
                "path",
                "header",
            }
        )

        validation_errors.append(
            {
                "field": field or None,
                "message": str(
                    error.get(
                        "msg",
                        "Invalid value",
                    )
                ),
                "error_type": str(
                    error.get(
                        "type",
                        "validation_error",
                    )
                ),
            }
        )

    logger.warning(
        "Request validation failed",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        validation_error_count=len(validation_errors),
    )

    return build_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        error_code="REQUEST_VALIDATION_ERROR",
        message="The request contains invalid or missing data",
        request_id=request_id,
        details={
            "validation_errors": validation_errors,
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle unexpected errors without exposing internal details"""

    request_id = get_request_id(request)

    logger.exception(
        "Unhandled server exception",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        exception_type=type(exc).__name__,
    )

    return build_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code="INTERNAL_SERVER_ERROR",
        message="An unexpected server error occurred",
        request_id=request_id,
    )


app.include_router(api_router)
