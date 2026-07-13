"""Defines the MarkdownParser class for processing markdown documents."""

from uuid import UUID

import markdown
from bs4 import BeautifulSoup

from src.documents.canonical import (
    CanonicalDocument,
    DocumentMetadata,
)
from src.parsing.baseParser import BaseParser


class MarkdownParser(BaseParser):
    """Markdown document stream parser."""

    def parse(self, data: bytes, document_id: UUID) -> CanonicalDocument:
        """Parse Markdown bytes into a CanonicalDocument structure."""
        raw_text = data.decode("utf-8", errors="replace")
        html_content = markdown.markdown(raw_text, extensions=["tables"])
        soup = BeautifulSoup(html_content, "html.parser")
        text = soup.get_text("\n")
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        doc_metadata = DocumentMetadata(
            schema_version="1.0.0",
            parser_name="MarkdownParser",
            parser_version="1.0.0",
        )

        blocks = []
        for index, line in enumerate(lines):
            block = self.create_default_block(document_id, line, index, page_number=1)
            blocks.append(block)

        return CanonicalDocument(
            document_id=document_id,
            metadata=doc_metadata,
            blocks=blocks,
        )
