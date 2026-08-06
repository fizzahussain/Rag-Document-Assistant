from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.schemas.common import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="healthy", database="unchecked", vector_db="postgresql")


@router.get("/ready", response_model=HealthResponse)
async def readiness_check(
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> HealthResponse:
    database_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        database_status = "error"

    ready = database_status == "connected"
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        status="ready" if ready else "not_ready",
        database=database_status,
        vector_db="postgresql" if ready else "error",
    )
