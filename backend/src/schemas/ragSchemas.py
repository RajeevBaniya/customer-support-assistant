from uuid import UUID

from src.schemas.commonSchemas import ApiModel


class CitationItem(ApiModel):
    document_id: UUID
    document_name: str
    source_page: int | None
    chunk_index: int


class RagAskResponse(ApiModel):
    answer: str
    citations: list[CitationItem]
    provider: str
    retrieval_top_k: int
