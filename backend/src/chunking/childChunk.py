"""Defines the ChildChunk Pydantic model representing an embedding-granular child chunk."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChildChunk(BaseModel):
    """Represents a smaller, embedding-optimized child chunk.

    Maintains a strict parent-child mapping back to its parent DocChunk
    to enable parent context expansion during generation.
    """

    model_config = ConfigDict(frozen=True)

    child_id: UUID = Field(
        ...,
        description="The unique identifier of this child chunk.",
    )
    parent_id: UUID = Field(
        ...,
        description="The identifier of the parent DocChunk this child belongs to.",
    )
    text: str = Field(
        ...,
        description="The text content of this child chunk.",
    )
    document_id: UUID = Field(
        ...,
        description="The unique identifier of the source document.",
    )
    block_ids: list[str] = Field(
        default_factory=list,
        description="The block IDs that intersect with this child chunk.",
    )
    block_types: list[str] = Field(
        default_factory=list,
        description="The block types associated with the child block metadata.",
    )
    page_numbers: list[int] = Field(
        default_factory=list,
        description="The page numbers associated with this child chunk.",
    )
    source_orders: list[int] = Field(
        default_factory=list,
        description="The list of source order values for the matched blocks.",
    )
    hierarchy_levels: list[int] = Field(
        default_factory=list,
        description="The list of hierarchy levels for the matched blocks.",
    )
    parser_version: str = Field(
        ...,
        description="The version of the parser used.",
    )
    schema_version: str = Field(
        ...,
        description="The schema version of the canonical representation.",
    )
    parser_confidence: list[float] = Field(
        default_factory=list,
        description="The list of parser confidence scores for each block.",
    )
    structure_confidence: list[float] = Field(
        default_factory=list,
        description="The list of structure detection confidence scores for each block.",
    )

    # Hierarchical and metadata fields for Phase 23
    section_id: UUID | None = Field(
        default=None,
        description="The unique section identifier this chunk belongs to.",
    )
    section_title: str | None = Field(
        default=None,
        description="The heading/section title this chunk belongs to.",
    )
    chunk_index: int = Field(
        default=0,
        description="The sequential index of the chunk in the parent/document context.",
    )
    chunk_hash: str = Field(
        default="",
        description="The SHA-256 hash of the normalized child chunk content.",
    )
    ingestion_version: str = Field(
        default="1.0.0",
        description="The ingestion version configured at the time of processing.",
    )
    workspace_id: UUID | None = Field(
        default=None,
        description="The workspace identifier (mapped to organization_id).",
    )
