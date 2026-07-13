"""Defines the PdfParser class for processing PDF documents."""

from io import BytesIO
from uuid import UUID

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from src.documents.canonical import (
    CanonicalDocument,
    DocumentMetadata,
)
from src.parsing.baseParser import BaseParser


class PdfParser(BaseParser):
    """Portable Document Format (.pdf) parser."""

    def parse(self, data: bytes, document_id: UUID) -> CanonicalDocument:
        """Parse PDF bytes into a CanonicalDocument structure."""
        try:
            reader = PdfReader(BytesIO(data), strict=False)
            pages = reader.pages
        except (PdfReadError, OSError, ValueError) as exception:
            raise ValueError(f"Failed to read PDF file structures: {exception}") from exception

        doc_metadata = DocumentMetadata(
            schema_version="1.0.0",
            parser_name="PdfParser",
            parser_version="1.0.0",
        )

        blocks = []
        index = 0
        for page_index, page in enumerate(pages):
            page_number = page_index + 1
            try:
                page_text = page.extract_text() or ""
            except Exception:
                page_text = ""

            page_text = page_text.strip()
            if not page_text:
                continue

            raw_paragraphs = [paragraph.strip() for paragraph in page_text.split("\n\n")]
            paragraphs = [paragraph for paragraph in raw_paragraphs if paragraph]

            for paragraph in paragraphs:
                block = self.create_default_block(
                    document_id, paragraph, index, page_number=page_number
                )
                blocks.append(block)
                index += 1

        return CanonicalDocument(
            document_id=document_id,
            metadata=doc_metadata,
            blocks=blocks,
        )
