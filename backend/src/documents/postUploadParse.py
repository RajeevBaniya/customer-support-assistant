from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from src.chunking.chunkMetadata import build_previews, chunk_pages_for_starts
from src.chunking.chunkStrategy import chunk_plain_text
from src.parsing.documentParser import parse_uploaded_bytes
from src.schemas.chunkSchemas import ChunkPreviewItem


@dataclass
class ParseChunkOutcome:
    parsing_status: str
    parser_type: str | None
    chunk_count: int
    previews: list[ChunkPreviewItem]
    parse_error: str | None
    parsed_at: datetime | None
    chunk_texts: list[str] = field(default_factory=list)
    chunk_pages: list[int | None] = field(default_factory=list)


async def run_parse_and_preview(
    *,
    document_id: UUID,
    mime_type: str,
    data: bytes,
) -> ParseChunkOutcome:
    try:
        payload = await parse_uploaded_bytes(mime_type=mime_type, data=data)
    except ValueError as exc:
        return ParseChunkOutcome(
            parsing_status="failed",
            parser_type=None,
            chunk_count=0,
            previews=[],
            parse_error=str(exc),
            parsed_at=None,
        )
    except Exception as exc:
        return ParseChunkOutcome(
            parsing_status="failed",
            parser_type=None,
            chunk_count=0,
            previews=[],
            parse_error=str(exc),
            parsed_at=None,
        )
    chunks, starts = chunk_plain_text(payload.text)
    previews = build_previews(
        document_id=document_id,
        parser_key=payload.parser_key,
        chunks=chunks,
        starts=starts,
        page_for_char=payload.page_for_char,
        max_chunks=5,
        preview_len=200,
    )
    pages = chunk_pages_for_starts(starts, payload.page_for_char)
    return ParseChunkOutcome(
        parsing_status="parsed",
        parser_type=payload.parser_key,
        chunk_count=len(chunks),
        previews=previews,
        parse_error=None,
        parsed_at=datetime.now(UTC),
        chunk_texts=list(chunks),
        chunk_pages=pages,
    )
