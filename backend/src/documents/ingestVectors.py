from datetime import UTC, datetime

from src.core.appEnvironment import AppEnvironment
from src.documents.ingestionRetryPolicy import (
    IngestionTransientError,
    is_transient_ingestion_failure,
)
from src.documents.postUploadParse import ParseChunkOutcome
from src.embeddings.embeddingService import embed_document_chunks
from src.models.documentModel import Document
from src.vectorstore.pineconeStore import build_pinecone_store
from src.vectorstore.vectorMetadata import build_chunk_metadata, chunk_vector_id


def _purge_document_vectors(settings: AppEnvironment, row: Document) -> None:
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
    settings: AppEnvironment,
    row: Document,
    parsed: ParseChunkOutcome,
    raise_transient: bool = False,
) -> None:
    if parsed.parsing_status != "parsed":
        row.embedding_status = "skipped"
        row.vector_count = 0
        row.embedding_model = None
        row.embedded_at = None
        return
    if not settings.pinecone_configured():
        row.embedding_status = "failed"
        row.vector_count = 0
        row.embedding_model = None
        row.embedded_at = None
        return
    texts = parsed.chunk_texts
    if not texts:
        row.embedding_status = "embedded"
        row.vector_count = 0
        row.embedded_at = datetime.now(UTC)
        row.embedding_model = settings.resolved_embedding_model
        return
    try:
        vectors = await embed_document_chunks(settings, texts)
        if len(vectors) != len(texts):
            raise RuntimeError("embedding_count_mismatch")
        store = build_pinecone_store(settings)
        _purge_document_vectors(settings, row)
        ids = [chunk_vector_id(row.organization_id, row.id, i) for i in range(len(texts))]
        metadatas = [
            build_chunk_metadata(
                document_id=row.id,
                organization_id=row.organization_id,
                chunk_index=i,
                parser_type=row.parser_type,
                source_page=parsed.chunk_pages[i] if i < len(parsed.chunk_pages) else None,
                document_created_at=row.created_at,
            )
            for i in range(len(texts))
        ]
        store.upsert_chunks(
            ids=ids,
            embeddings=vectors,
            documents=texts,
            metadatas=metadatas,
        )
        row.embedding_status = "embedded"
        row.vector_count = len(texts)
        row.embedded_at = datetime.now(UTC)
        row.embedding_model = settings.resolved_embedding_model
    except Exception as exc:
        _purge_document_vectors(settings, row)
        if raise_transient and is_transient_ingestion_failure(exc):
            raise IngestionTransientError(str(exc)) from exc
        row.embedding_status = "failed"
        row.vector_count = 0
        row.embedding_model = None
        row.embedded_at = None
