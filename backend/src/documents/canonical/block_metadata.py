"""Defines the BlockMetadata model representing metadata for a specific document block."""

from pydantic import BaseModel, ConfigDict, Field


class BlockMetadata(BaseModel):
    """Metadata specific to a DocumentBlock.

    Provides positional, page-based, and extra metadata extension points.
    All properties are immutable.
    """

    model_config = ConfigDict(frozen=True)

    page_number: int | None = Field(
        default=None,
        description="The 1-indexed page number where this block is located in the source document.",
    )
    coordinates: list[float] | None = Field(
        default=None,
        description=(
            "Bounding box coordinates [x0, y0, x1, y1] "
            "indicating the location of the block on the page."
        ),
    )
    extra_metadata: dict[str, object] = Field(
        default_factory=dict,
        description="A dictionary for parser-specific attributes and custom extensions.",
    )
