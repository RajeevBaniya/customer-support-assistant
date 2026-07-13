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
        description="The list of parser confidence scores for the blocks.",
    )
    structure_confidence: list[float] = Field(
        default_factory=list,
        description="The list of structure detection confidence scores for the blocks.",
    )
