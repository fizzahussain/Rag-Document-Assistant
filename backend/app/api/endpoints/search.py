from fastapi import APIRouter

from backend.app.schemas.search import SearchRequest, SearchResponse
from backend.app.services.retrieval import RetrievalService

router = APIRouter(tags=["Search"])


@router.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest) -> SearchResponse:
    """Executes dense vector search across user documents."""
    retrieval_service = RetrievalService()

    doc_ids_str = (
        [str(d) for d in request.document_ids] if request.document_ids else None
    )

    results = await retrieval_service.search(
        query=request.query,
        user_id=str(request.user_id),
        limit=request.limit,
        score_threshold=request.score_threshold,
        document_ids=doc_ids_str,
        workspace_id=request.workspace_id,
    )

    return SearchResponse(
        query=request.query,
        total_results=len(results),
        results=results,
    )
