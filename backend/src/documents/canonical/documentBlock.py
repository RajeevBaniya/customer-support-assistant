"""Defines the DocumentBlock model representing a structural element of a document."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.documents.canonical.blockMetadata import BlockMetadata
from src.documents.canonical.blockType import BlockType


class DocumentBlock(BaseModel):
    """Represents a single structural element inside a document.

    Each block is typed, ordered, and contains its parsed content and metadata.
    All properties are immutable.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(
        ...,
        description="A unique identifier for the block (e.g. UUID string or UUID itself).",
    )
    type: BlockType = Field(
        default=BlockType.UNKNOWN,
        description="The type of the structural element (e.g. paragraph, heading).",
    )
    content: str = Field(
        ...,
        description="The extracted raw text content of the block.",
    )
    parser_confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="The confidence score of the parser for this block, from 0.0 to 1.0.",
    )
    parent_id: str | None = Field(
        default=None,
        description="The unique identifier of the parent block, if nested structurally.",
    )
    hierarchy_level: int = Field(
        default=0,
        ge=0,
        description="The depth of nesting or hierarchy level of the block (0 for root).",
    )
    source_order: int = Field(
        default=0,
        ge=0,
        description="The exact appearance sequence number in the source file layout.",
    )
    index: int = Field(
        ...,
        ge=0,
        description="The logical index used for ordering blocks sequentially.",
    )
    metadata: BlockMetadata = Field(
        default_factory=BlockMetadata,
        description="Positional, page-based, and extra metadata specific to this block.",
    )

    @field_validator("type", mode="before")
    @classmethod
    def fallback_unknown(cls, value: object) -> BlockType:
        """Falls back to BlockType.UNKNOWN if the input string does not match any enum value."""
        if isinstance(value, str):
            try:
                return BlockType(value.lower())
            except ValueError:
                return BlockType.UNKNOWN
        if isinstance(value, BlockType):
            return value
        return BlockType.UNKNOWN
