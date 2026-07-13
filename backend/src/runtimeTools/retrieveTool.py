"""RetrieveTool wrapping document semantic search capabilities."""

from uuid import UUID

from pydantic import BaseModel, Field

from src.retrieval.retrievalService import RetrievalService
from src.runtimeTools.baseTool import BaseTool
from src.schemas.retrievalSchemas import RetrievalSearchRequest, RetrievalSearchResponse


class RetrieveRequest(BaseModel):
    """Request schema for RetrieveTool execution."""

    query: str = Field(min_length=1)
    organization_id: UUID
    document_ids: list[UUID] | None = None
    top_k: int | None = None


class RetrieveTool(BaseTool):
    """Semantic search and layout-aware chunk retrieval tool."""

    async def retrieve(self, request: RetrieveRequest) -> RetrievalSearchResponse:
        """Execute semantic retrieval pipeline."""
        service = RetrievalService(self._session, self._settings)
        retrieval_request = RetrievalSearchRequest(
            query=request.query,
            top_k=request.top_k,
            document_ids=request.document_ids,
        )
        return await service.search(
            organization_id=request.organization_id,
            body=retrieval_request,
        )
