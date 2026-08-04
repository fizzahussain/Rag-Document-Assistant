import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import get_current_user_id
from backend.app.database import get_db
from backend.app.schemas.search import SearchRequest, SearchResponse
from backend.app.services.retrieval import RetrievalService

router = APIRouter(tags=["Search"])


@router.post("/search", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    results = await RetrievalService(db).search(
        query=request.query,
        user_id=current_user_id,
        limit=request.limit,
        score_threshold=request.score_threshold,
        document_ids=request.document_ids,
        workspace_id=request.workspace_id,
    )
    return SearchResponse(
        query=request.query,
        total_results=len(results),
        results=results,
    )
