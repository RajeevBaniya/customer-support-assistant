from uuid import UUID

from pydantic import Field

from src.schemas.commonSchemas import ApiModel


class ChunkPreviewItem(ApiModel):
    chunk_index: int = Field(ge=0)
    source_document_id: UUID
    source_page: int | None = None
    character_count: int = Field(ge=0)
    token_estimate: int = Field(ge=1)
    parser_type: str
    preview_text: str = Field(max_length=200)
