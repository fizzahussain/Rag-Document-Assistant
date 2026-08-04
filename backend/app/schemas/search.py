import uuid

from pydantic import BaseModel, Field

from backend.app.services.retrieval import RetrievedSource


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    limit: int = Field(default=5, ge=1, le=50)
    score_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    document_ids: list[uuid.UUID] | None = None
    workspace_id: str | None = None


class SearchResponse(BaseModel):
    query: str
    total_results: int
    results: list[RetrievedSource]
