"""Defines the CanonicalDocument model representing a format-agnostic parsed document layout."""

from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.documents.canonical.document_block import DocumentBlock
from src.documents.canonical.document_metadata import DocumentMetadata


class CanonicalDocument(BaseModel):
    """The universal internal document representation.

    Every document, once parsed from its original format, is converted to this format
    prior to semantic chunking. All properties are immutable.
    """

    model_config = ConfigDict(frozen=True)

    document_id: UUID = Field(
        ...,
        description="The unique identifier of the document.",
    )
    metadata: DocumentMetadata = Field(
        ...,
        description="Global document metadata.",
    )
    blocks: list[DocumentBlock] = Field(
        default_factory=list,
        description="The ordered list of blocks representing the structural text layout.",
    )

    @model_validator(mode="after")
    def validate_document_structure(self) -> Self:
        """Validates structural constraints of the canonical document.

        Checks:
        1. Unique Block IDs to prevent identity collisions.
        2. Orphan parent ID references.
        3. Index ordering compliance.
        4. Duplicate source_order values.
        5. Negative hierarchy_level or source_order values.
        6. Empty block content for non-UNKNOWN types.
        """
        block_ids = set()
        source_orders = set()

        for block in self.blocks:
            if block.id in block_ids:
                raise ValueError(f"Duplicate block ID detected: {block.id}")
            block_ids.add(block.id)

            if block.source_order in source_orders:
                raise ValueError(f"Duplicate source_order detected: {block.source_order}")
            source_orders.add(block.source_order)

            if block.hierarchy_level < 0:
                raise ValueError(f"Negative hierarchy_level: {block.hierarchy_level}")
            if block.source_order < 0:
                raise ValueError(f"Negative source_order: {block.source_order}")

            from src.documents.canonical.block_type import BlockType

            if block.type != BlockType.UNKNOWN and not block.content.strip():
                raise ValueError(f"Empty content not allowed for block type: {block.type}")

        for block in self.blocks:
            if block.parent_id is not None and block.parent_id not in block_ids:
                raise ValueError(
                    f"Orphan block detected: parent_id '{block.parent_id}' does not exist"
                )

        sorted_blocks = sorted(self.blocks, key=lambda b: b.index)
        for i, block in enumerate(self.blocks):
            if block.id != sorted_blocks[i].id:
                raise ValueError("Blocks list must be sorted in ascending order by index")

        return self
