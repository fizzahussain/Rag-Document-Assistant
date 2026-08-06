import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import RAGException, RetrievalError
from backend.app.core.security import get_current_user_id
from backend.app.database import get_db
from backend.app.schemas.common import ErrorResponse
from backend.app.schemas.search import SearchRequest, SearchResponse
from backend.app.services.retrieval import RetrievalService

router = APIRouter(
    tags=["Search"],
)


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Search document content",
    description=(
        "Search indexed chunks belonging to the authenticated user using "
        "semantic similarity and optional document or workspace filters."
    ),
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Authentication credentials are missing or invalid",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErrorResponse,
            "description": "The search request is invalid",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ErrorResponse,
            "description": "The retrieval service is unavailable",
        },
    },
)
async def search_documents(
    request: SearchRequest,
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """Search indexed content owned by the authenticated user"""

    retrieval = RetrievalService(db)

    try:
        results = await retrieval.search(
            query=request.query,
            user_id=current_user_id,
            limit=request.limit,
            score_threshold=request.score_threshold,
            document_ids=request.document_ids,
            workspace_id=request.workspace_id,
        )
    except RAGException:
        raise
    except Exception as exc:
        raise RetrievalError(
            message="Document search could not be completed",
            details={
                "service": "retrieval",
            },
        ) from exc

    return SearchResponse(
        query=request.query,
        total_results=len(results),
        results=results,
    )
