"""Defines the TextParser class for processing plain text documents."""

from uuid import UUID

from src.documents.canonical import (
    CanonicalDocument,
    DocumentMetadata,
)
from src.parsing.baseParser import BaseParser


class TextParser(BaseParser):
    """Plain text document stream parser."""

    def parse(self, data: bytes, document_id: UUID) -> CanonicalDocument:
        """Parse plain text bytes into a CanonicalDocument structure."""
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("utf-8", errors="replace")

        text = text.strip()
        doc_metadata = DocumentMetadata(
            schema_version="1.0.0",
            parser_name="TextParser",
            parser_version="1.0.0",
        )

        if not text:
            return CanonicalDocument(
                document_id=document_id,
                metadata=doc_metadata,
                blocks=[],
            )

        raw_paragraphs = [paragraph.strip() for paragraph in text.split("\n\n")]
        paragraphs = [paragraph for paragraph in raw_paragraphs if paragraph]

        blocks = []
        for index, paragraph in enumerate(paragraphs):
            block = self.create_default_block(document_id, paragraph, index, page_number=1)
            blocks.append(block)

        return CanonicalDocument(
            document_id=document_id,
            metadata=doc_metadata,
            blocks=blocks,
        )
