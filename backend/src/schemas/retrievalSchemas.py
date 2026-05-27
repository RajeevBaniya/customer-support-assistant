from datetime import datetime
from uuid import UUID

from pydantic import Field

from src.schemas.commonSchemas import ApiModel


class RetrievalSearchRequest(ApiModel):
    query: str = Field(min_length=3, max_length=2000)
    top_k: int | None = Field(default=None, ge=1, le=50)
    document_ids: list[UUID] | None = None


class RetrievalChunkItem(ApiModel):
    document_id: UUID
    document_name: str
    chunk_index: int
    source_page: int | None
    similarity_score: float
    parser_type: str | None
    text: str
    upload_timestamp: datetime


class RetrievalSearchResponse(ApiModel):
    items: list[RetrievalChunkItem]
    query: str
    top_k: int
