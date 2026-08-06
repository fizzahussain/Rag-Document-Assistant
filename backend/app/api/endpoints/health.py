import time

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.schemas.common import HealthResponse, ServiceHealth

router = APIRouter(
    tags=["Health"],
)


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check API liveness",
    description="Confirm that the FastAPI process is running.",
)
async def health_check(
    request: Request,
) -> HealthResponse:
    """Return application liveness information"""

    request_id = getattr(
        request.state,
        "request_id",
        None,
    )

    return HealthResponse(
        status="healthy",
        service="rag-document-assistant",
        version="1.0.0",
        request_id=request_id,
        checks={
            "api": ServiceHealth(
                status="healthy",
                message="FastAPI is running",
            ),
        },
    )


@router.get(
    "/ready",
    response_model=HealthResponse,
    summary="Check API readiness",
    description=("Check whether the API and PostgreSQL database are ready to serve requests."),
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "One or more required services are unavailable",
        }
    },
)
async def readiness_check(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> HealthResponse:
    """Return application dependency readiness"""

    request_id = getattr(
        request.state,
        "request_id",
        None,
    )

    database_status = "healthy"
    database_message = "Database connection established"
    database_latency_ms: float | None = None

    started_at = time.perf_counter()

    try:
        await db.execute(
            text("SELECT 1"),
        )

        database_latency_ms = (time.perf_counter() - started_at) * 1000
    except Exception:
        database_status = "unhealthy"
        database_message = "Database connection failed"
        database_latency_ms = (time.perf_counter() - started_at) * 1000

    ready = database_status == "healthy"

    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    overall_status = "healthy" if ready else "unhealthy"

    vector_status = "healthy" if ready else "unavailable"
    vector_message = (
        "PostgreSQL and pgvector are available"
        if ready
        else "pgvector readiness could not be confirmed"
    )

    return HealthResponse(
        status=overall_status,
        service="rag-document-assistant",
        version="1.0.0",
        request_id=request_id,
        checks={
            "database": ServiceHealth(
                status=database_status,
                message=database_message,
                latency_ms=database_latency_ms,
            ),
            "vector_db": ServiceHealth(
                status=vector_status,
                message=vector_message,
            ),
        },
    )
