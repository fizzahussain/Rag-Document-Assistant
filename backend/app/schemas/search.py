from typing import List, Optional
import uuid
from pydantic import BaseModel, Field
from backend.app.services.retrieval import RetrievedSource


class SearchRequest(BaseModel):
    """Semantic vector search request model."""

    user_id: uuid.UUID = Field(..., description="ID of the user performing search")
    query: str = Field(..., min_length=1, description="Search query string")
    limit: int = Field(default=5, ge=1, le=50, description="Max search results to return")
    score_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Similarity score threshold")
    document_ids: Optional[List[uuid.UUID]] = Field(default=None, description="Filter search by document IDs")
    workspace_id: Optional[str] = Field(default=None, description="Filter search by workspace ID")


class SearchResponse(BaseModel):
    """Semantic vector search response model."""

    query: str
    total_results: int
    results: List[RetrievedSource]
