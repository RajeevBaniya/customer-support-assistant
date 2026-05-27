import asyncio
import time
from uuid import UUID

from src.core.appEnvironment import AppEnvironment
from src.embeddings.embeddingService import embed_query_text
from src.vectorstore.pineconeStore import build_pinecone_store
from src.vectorstore.queryHit import VectorQueryHit
from src.vectorstore.vectorStore import VectorStore


async def run_vector_query(
    *,
    settings: AppEnvironment,
    store: VectorStore,
    organization_id: UUID,
    query: str,
    fetch_limit: int,
    document_ids: list[UUID] | None,
) -> tuple[list[VectorQueryHit], dict[str, float]]:
    t_embed0 = time.perf_counter()
    embedding = await embed_query_text(settings, query)
    t_embed1 = time.perf_counter()
    org_s = str(organization_id)
    doc_filter = [str(d) for d in document_ids] if document_ids else None

    def _query() -> list[VectorQueryHit]:
        return store.semantic_search(
            query_embedding=embedding,
            organization_id=org_s,
            limit=fetch_limit,
            document_ids=doc_filter,
        )

    t_vec0 = time.perf_counter()
    hits = await asyncio.to_thread(_query)
    t_vec1 = time.perf_counter()
    timings = {
        "embed_ms": round((t_embed1 - t_embed0) * 1000.0, 3),
        "pinecone_ms": round((t_vec1 - t_vec0) * 1000.0, 3),
    }
    return hits, timings


def build_vector_store(settings: AppEnvironment) -> VectorStore:
    return build_pinecone_store(settings)
