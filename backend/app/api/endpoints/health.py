from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.database import get_db
from backend.app.schemas.common import HealthResponse
from backend.app.services.qdrant import QdrantService

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    """Checks operational status of PostgreSQL and Qdrant vector database."""
    db_status = "disconnected"
    qdrant_status = "disconnected"

    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "error"

    try:
        qdrant = QdrantService()
        await qdrant.init_collection()
        qdrant_status = "connected"
    except Exception:
        qdrant_status = "degraded"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "unhealthy",
        database=db_status,
        vector_db=qdrant_status,
    )


@router.get("/ready")
async def readiness_check() -> dict:
    """Readiness probe for container orchestration."""
    return {"status": "ready"}
