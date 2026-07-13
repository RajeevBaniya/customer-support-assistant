"""Modernized embedding pipeline and database transaction logic."""

from datetime import UTC, datetime
from time import perf_counter

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.appEnvironment import AppEnvironment
from src.documents.childChunkRepository import ChildChunkRepository
from src.documents.ingestionMetadataRepository import IngestionMetadataRepository
from src.documents.ingestionRetryPolicy import (
    IngestionTransientError,
    is_transient_ingestion_failure,
)
from src.documents.parentChunkRepository import ParentChunkRepository
from src.documents.postUploadParse import ParseChunkOutcome
from src.embeddings.embeddingService import embed_document_chunks
from src.models.childChunkModel import ChildChunk as ChildChunkRow
from src.models.documentModel import Document
from src.models.ingestionMetadataModel import IngestionMetadata as IngestionMetadataRow
from src.models.parentChunkModel import ParentChunk as ParentChunkRow
from src.observability.structuredLogger import get_logger
from src.vectorstore.pineconeStore import build_pinecone_store
from src.vectorstore.vectorMetadata import (
    build_parent_chunk_vector_metadata,
    chunk_vector_id,
)

logger = get_logger("ingestion.storage")


def _purge_document_vectors(settings: AppEnvironment, row: Document) -> None:
    """Purges all vectors for the document from Pinecone."""
    if not settings.pinecone_configured():
        return
    try:
        store = build_pinecone_store(settings)
        store.delete_document_vectors(
            organization_id=str(row.organization_id),
            document_id=str(row.id),
        )
    except Exception:
        pass


async def run_embedding_ingest(
    *,
    session: AsyncSession,
    settings: AppEnvironment,
    row: Document,
    parsed: ParseChunkOutcome,
    raise_transient: bool = False,
) -> None:
    """Persists Parent/Child metadata rows to PostgreSQL and child vectors to Pinecone.

    Commit operations are coordinated at the transaction orchestrator level.
    """
    if parsed.parsing_status != "parsed":
        _mark_skipped_or_failed(row, "skipped")
        return

    if not settings.pinecone_configured():
        _mark_skipped_or_failed(row, "failed")
        return

    texts = parsed.chunk_texts
    if not texts:
        row.embedding_status = "embedded"
        row.vector_count = 0
        row.embedded_at = datetime.now(UTC)
        row.embedding_model = settings.resolved_embedding_model
        return

    try:
        # 1. Clean and persist parent/child records to PostgreSQL
        t_db_start = perf_counter()
        parent_rows, child_rows = await _persist_to_postgres(session, row, parsed)
        db_duration = perf_counter() - t_db_start

        # 2. Generate vectors via batched embedding pipeline
        vectors = await embed_document_chunks(settings, texts)
        if len(vectors) != len(texts):
            raise RuntimeError("embedding_count_mismatch")

        # 3. Perform Pinecone vector storage upserts
        t_store_start = perf_counter()
        _upsert_to_pinecone(settings, row, parsed, vectors)
        store_duration = perf_counter() - t_store_start

        # 4. Update status properties on document
        row.embedding_status = "embedded"
        row.vector_count = len(texts)
        row.embedded_at = datetime.now(UTC)
        row.embedding_model = settings.resolved_embedding_model

        logger.info(
            "knowledge_storage_completed",
            postgres_storage_duration_seconds=round(db_duration, 4),
            pinecone_storage_duration_seconds=round(store_duration, 4),
            parents_stored=len(parent_rows),
            children_stored=len(child_rows),
            vectors_stored=len(texts),
            success=True,
        )

    except Exception as exc:
        await session.rollback()
        _purge_document_vectors(settings, row)
        _mark_skipped_or_failed(row, "failed")
        if raise_transient and is_transient_ingestion_failure(exc):
            raise IngestionTransientError(str(exc)) from exc
        raise


def _mark_skipped_or_failed(row: Document, status: str) -> None:
    """Helper to reset document embedding fields on failure or skip."""
    row.embedding_status = status
    row.vector_count = 0
    row.embedding_model = None
    row.embedded_at = None


async def _persist_to_postgres(
    session: AsyncSession,
    row: Document,
    parsed: ParseChunkOutcome,
) -> tuple[list[ParentChunkRow], list[ChildChunkRow]]:
    """Clean existing entries and save parent/child document records in DB."""
    parent_repo = ParentChunkRepository(session)
    child_repo = ChildChunkRepository(session)
    meta_repo = IngestionMetadataRepository(session)

    await parent_repo.delete_by_document_id(row.id)
    await meta_repo.delete_by_document_id(row.id)

    parent_rows = [
        ParentChunkRow(
            id=p.parent_id,
            document_id=row.id,
            text=p.text,
            block_ids=p.block_ids,
            block_types=p.block_types,
            page_numbers=p.page_numbers,
            source_orders=p.source_orders,
            hierarchy_levels=p.hierarchy_levels,
            parser_confidence=p.parser_confidence,
            structure_confidence=p.structure_confidence,
        )
        for p in parsed.chunks
    ]
    await parent_repo.add_all(parent_rows)

    child_rows = [
        ChildChunkRow(
            id=c.child_id,
            parent_id=c.parent_id,
            document_id=row.id,
            text=c.text,
            block_ids=c.block_ids,
            block_types=c.block_types,
            page_numbers=c.page_numbers,
            source_orders=c.source_orders,
            hierarchy_levels=c.hierarchy_levels,
            parser_confidence=c.parser_confidence,
            structure_confidence=c.structure_confidence,
        )
        for c in parsed.child_chunks
    ]
    await child_repo.add_all(child_rows)

    meta_row = IngestionMetadataRow(
        document_id=row.id,
        parser_name=parsed.parser_type or "unknown",
        parser_version=parsed.parser_version,
        schema_version=parsed.schema_version,
        fallback_usage_count=parsed.fallback_usage_count,
        overlap_usage_count=parsed.overlap_usage_count,
        parsing_duration_seconds=parsed.parsing_duration_seconds,
        chunking_duration_seconds=parsed.chunking_duration_seconds,
        mapping_duration_seconds=parsed.mapping_duration_seconds,
    )
    await meta_repo.add(meta_row)
    return parent_rows, child_rows


def _upsert_to_pinecone(
    settings: AppEnvironment,
    row: Document,
    parsed: ParseChunkOutcome,
    vectors: list[list[float]],
) -> None:
    """Upsert generated chunk embeddings to Pinecone index."""
    store = build_pinecone_store(settings)
    _purge_document_vectors(settings, row)

    texts = parsed.chunk_texts
    ids = [chunk_vector_id(row.organization_id, row.id, i) for i in range(len(texts))]
    metadatas = [
        build_parent_chunk_vector_metadata(
            parent=p,
            organization_id=row.organization_id,
            uploaded_at=row.created_at,
        )
        for p in parsed.chunks
    ]
    store.upsert_chunks(
        ids=ids,
        embeddings=vectors,
        documents=texts,
        metadatas=metadatas,
    )
