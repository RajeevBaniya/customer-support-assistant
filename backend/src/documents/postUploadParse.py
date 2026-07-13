"""Exposes ingestion parsing and previews builder outcomes."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import perf_counter
from uuid import UUID

from src.chunking import ChildChunk, DocChunk, ParentChildBuilder, StructureAwareChunker
from src.chunking.chunkMetadata import token_estimate
from src.core.appEnvironment import AppEnvironment
from src.documents.canonical import CanonicalDocument
from src.observability.structuredLogger import get_logger
from src.parsing.documentParser import parse_to_canonical
from src.parsing.parserRegistry import parser_key_for_mime
from src.schemas.chunkSchemas import ChunkPreviewItem

logger = get_logger("ingestion.chunking")


@dataclass
class ParseChunkOutcome:
    """Dataclass holding ingestion outcome for downstream vector stores."""

    parsing_status: str
    parser_type: str | None
    chunk_count: int
    previews: list[ChunkPreviewItem]
    parse_error: str | None
    parsed_at: datetime | None
    chunk_texts: list[str] = field(default_factory=list)
    chunk_pages: list[int | None] = field(default_factory=list)
    chunks: list[DocChunk] = field(default_factory=list)
    child_chunks: list[ChildChunk] = field(default_factory=list)
    parser_version: str = "unknown"
    schema_version: str = "unknown"
    parsing_duration_seconds: float = 0.0
    chunking_duration_seconds: float = 0.0
    mapping_duration_seconds: float = 0.0
    fallback_usage_count: int = 0
    overlap_usage_count: int = 0


def build_previews_from_chunks(
    *,
    document_id: UUID,
    parser_key: str,
    chunks: list[DocChunk],
    max_chunks: int = 5,
    preview_len: int = 200,
) -> list[ChunkPreviewItem]:
    """Generates preview items for the UI from the structured chunk models."""
    out = []
    for idx, c in enumerate(chunks):
        if idx >= max_chunks:
            break
        preview = c.text[:preview_len]
        sp = c.page_numbers[0] if c.page_numbers else 1
        out.append(
            ChunkPreviewItem(
                chunk_index=idx,
                source_document_id=document_id,
                source_page=sp,
                character_count=len(c.text),
                token_estimate=token_estimate(c.text),
                parser_type=parser_key,
                preview_text=preview,
            )
        )
    return out


async def run_parse_and_preview(
    *,
    document_id: UUID,
    mime_type: str,
    data: bytes,
    settings: AppEnvironment | None = None,
) -> ParseChunkOutcome:
    """Parses a document to CanonicalDocument and runs parent-child chunking."""
    parser_key = parser_key_for_mime(mime_type) or "unknown"

    # 1. Parse & detect structures to CanonicalDocument
    try:
        doc, parsing_duration = await _parse_to_canonical_with_timer(mime_type, data)
    except Exception as exc:
        logger.error("parsing_failed", error=str(exc), success=False)
        return ParseChunkOutcome(
            parsing_status="failed",
            parser_type=None,
            chunk_count=0,
            previews=[],
            parse_error=str(exc),
            parsed_at=None,
        )

    # Load chunk config parameters from settings
    parent_size = settings.parent_chunk_size if settings is not None else 1200
    overlap = settings.chunk_overlap if settings is not None else 150
    child_size = settings.child_chunk_size if settings is not None else 400
    child_overlap = settings.child_chunk_overlap if settings is not None else 50

    # 2. Run Structure-aware chunking (generating initial parent chunks)
    try:
        parents, fallback_count, overlap_count, chunking_duration = await _run_chunker_with_timer(
            doc, parent_size, overlap
        )
    except Exception as exc:
        logger.error("chunking_failed", error=str(exc), success=False)
        return ParseChunkOutcome(
            parsing_status="failed",
            parser_type=parser_key,
            chunk_count=0,
            previews=[],
            parse_error=str(exc),
            parsed_at=None,
        )

    # 3. Partition parents into overlapping, mapped child chunks
    try:
        evolved_parents, child_chunks, map_duration = await _run_builder_with_timer(
            parents, child_size, child_overlap
        )
    except Exception as exc:
        logger.error("parent_child_mapping_failed", error=str(exc), success=False)
        return ParseChunkOutcome(
            parsing_status="failed",
            parser_type=parser_key,
            chunk_count=0,
            previews=[],
            parse_error=str(exc),
            parsed_at=None,
        )

    # 4. Generate previews and compatible outcome structures (referencing parent chunks)
    previews = build_previews_from_chunks(
        document_id=document_id,
        parser_key=parser_key,
        chunks=evolved_parents,
        max_chunks=5,
        preview_len=200,
    )

    chunk_texts = [p.text for p in evolved_parents]
    chunk_pages: list[int | None] = [
        (p.page_numbers[0] if p.page_numbers else None) for p in evolved_parents
    ]

    return ParseChunkOutcome(
        parsing_status="parsed",
        parser_type=parser_key,
        chunk_count=len(evolved_parents),
        previews=previews,
        parse_error=None,
        parsed_at=datetime.now(UTC),
        chunk_texts=chunk_texts,
        chunk_pages=chunk_pages,
        chunks=evolved_parents,
        child_chunks=child_chunks,
        parser_version=doc.metadata.parser_version,
        schema_version=doc.metadata.schema_version,
        parsing_duration_seconds=parsing_duration,
        chunking_duration_seconds=chunking_duration,
        mapping_duration_seconds=map_duration,
        fallback_usage_count=fallback_count,
        overlap_usage_count=overlap_count,
    )


async def _parse_to_canonical_with_timer(
    mime_type: str,
    data: bytes,
) -> tuple[CanonicalDocument, float]:
    """Parse document bytes and return CanonicalDocument with duration."""
    t_start = perf_counter()
    doc = await parse_to_canonical(mime_type=mime_type, data=data)
    return doc, perf_counter() - t_start


async def _run_chunker_with_timer(
    doc: CanonicalDocument,
    parent_size: int,
    overlap: int,
) -> tuple[list[DocChunk], int, int, float]:
    """Run structure aware chunker and return output with metrics and duration."""
    t_start = perf_counter()
    chunker = StructureAwareChunker(chunk_size=parent_size, overlap=overlap)
    parents = chunker.chunk(doc)
    duration = perf_counter() - t_start

    avg_size = sum(len(c.text) for c in parents) / len(parents) if parents else 0.0
    logger.info(
        "chunking_completed",
        chunk_count=len(parents),
        average_chunk_size_chars=round(avg_size, 2),
        chunking_duration_seconds=round(duration, 4),
        fallback_usage_count=chunker.fallback_count,
        overlap_usage_count=chunker.overlap_count,
        success=True,
    )
    return parents, chunker.fallback_count, chunker.overlap_count, duration


async def _run_builder_with_timer(
    parents: list[DocChunk],
    child_size: int,
    child_overlap: int,
) -> tuple[list[DocChunk], list[ChildChunk], float]:
    """Run parent child builder and return outputs with duration."""
    t_start = perf_counter()
    builder = ParentChildBuilder(
        child_chunk_size=child_size,
        child_chunk_overlap=child_overlap,
    )
    evolved_parents, child_chunks = builder.build_relations(parents)
    duration = perf_counter() - t_start

    avg_children = len(child_chunks) / len(evolved_parents) if evolved_parents else 0.0
    logger.info(
        "parent_child_mapping_completed",
        parent_count=len(evolved_parents),
        child_count=len(child_chunks),
        average_children_per_parent=round(avg_children, 2),
        mapping_duration_seconds=round(duration, 4),
        success=True,
    )
    return evolved_parents, child_chunks, duration
