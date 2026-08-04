from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.schemas.common import HealthResponse
from backend.app.services.qdrant import get_qdrant_service

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="healthy", database="unchecked", vector_db="unchecked")


@router.get("/ready", response_model=HealthResponse)
async def readiness_check(
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> HealthResponse:
    database_status = "connected"
    vector_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        database_status = "error"
    try:
        await get_qdrant_service().init_collection()
    except Exception:
        vector_status = "error"
    ready = database_status == "connected" and vector_status == "connected"
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(
        status="ready" if ready else "not_ready",
        database=database_status,
        vector_db=vector_status,
    )
