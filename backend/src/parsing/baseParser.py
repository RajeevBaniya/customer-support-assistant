"""Defines the BaseParser abstract base class representing the document parser interface."""

from abc import ABC, abstractmethod
from uuid import UUID

from src.documents.canonical import (
    BlockMetadata,
    BlockType,
    CanonicalDocument,
    DocumentBlock,
)


class BaseParser(ABC):
    """Abstract base class that all concrete document parsers must implement."""

    @abstractmethod
    def parse(self, data: bytes, document_id: UUID) -> CanonicalDocument:
        """Parse raw document bytes into a CanonicalDocument representation."""
        pass

    def create_default_block(
        self,
        document_id: UUID,
        content: str,
        index: int,
        page_number: int = 1,
    ) -> DocumentBlock:
        """Build a default PARAGRAPH DocumentBlock for parsed text segments."""
        return DocumentBlock(
            id=f"{document_id}-block-{index}",
            type=BlockType.PARAGRAPH,
            content=content,
            parser_confidence=1.0,
            parent_id=None,
            hierarchy_level=0,
            source_order=index,
            index=index,
            metadata=BlockMetadata(page_number=page_number),
        )
