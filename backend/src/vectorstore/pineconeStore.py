from typing import Any
from uuid import UUID

from pinecone import Pinecone

from src.core.appEnvironment import AppEnvironment
from src.vectorstore.queryHit import VectorQueryHit
from src.vectorstore.vectorStore import VectorStore


class PineconeVectorStore(VectorStore):
    """Pinecone vector store provider implementation."""

    def __init__(self, *, settings: AppEnvironment) -> None:
        key = (settings.pinecone_api_key or "").strip()
        index_name = (settings.pinecone_index_name or "").strip()
        if not key or not index_name:
            raise ValueError("pinecone_not_configured")
        pinecone_client = Pinecone(api_key=key)
        pinecone_client.indexes.describe(index_name)
        self._index = pinecone_client.Index(index_name)

    def upsert_chunks(
        self,
        *,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        """Upsert layout chunks and metadata to Pinecone in batches."""
        batch_size = 100
        for batch_start_index in range(0, len(ids), batch_size):
            batch: list[dict[str, Any]] = []
            limit_index = min(batch_start_index + batch_size, len(ids))
            for current_index in range(batch_start_index, limit_index):
                metadata = dict(metadatas[current_index])
                metadata["chunk_text"] = documents[current_index][:39000]
                batch.append({
                    "id": ids[current_index],
                    "values": embeddings[current_index],
                    "metadata": metadata,
                })
            self._index.upsert(vectors=batch, show_progress=False)

    def delete_document_vectors(self, *, organization_id: str, document_id: str) -> None:
        """Delete all vectors matching organization and document identifiers."""
        query_filter: dict[str, Any] = {
            "organization_id": {"$eq": organization_id},
            "document_id": {"$eq": document_id},
        }
        self._index.delete(filter=query_filter)

    def semantic_search(
        self,
        *,
        query_embedding: list[float],
        organization_id: str,
        limit: int,
        document_ids: list[str] | None,
    ) -> list[VectorQueryHit]:
        """Perform semantic search against organization context."""
        query_filter: dict[str, Any] = {"organization_id": {"$eq": organization_id}}
        if document_ids:
            query_filter["document_id"] = {"$in": document_ids}
        n_results = max(1, min(limit, 256))
        raw_response = self._index.query(
            top_k=n_results,
            vector=query_embedding,
            filter=query_filter,
            include_metadata=True,
        )
        matches = getattr(raw_response, "matches", None) or []
        hits: list[VectorQueryHit] = []
        for match in matches:
            raw_metadata = getattr(match, "metadata", None) or {}
            metadata = dict(raw_metadata) if isinstance(raw_metadata, dict) else {}
            raw_document_id = metadata.get("document_id")
            if not raw_document_id:
                continue
            try:
                document_id = UUID(str(raw_document_id))
            except ValueError:
                continue
            raw_chunk_index = metadata.get("chunk_index", 0)
            try:
                chunk_index = int(raw_chunk_index)
            except (TypeError, ValueError):
                chunk_index = 0
            score = float(getattr(match, "score", 0.0) or 0.0)
            distance = 1.0 - score
            vector_id = str(getattr(match, "id", "") or "")
            text = str(metadata.get("chunk_text", ""))
            hits.append(
                VectorQueryHit(
                    vector_id=vector_id,
                    document_id=document_id,
                    chunk_index=chunk_index,
                    distance=distance,
                    text=text,
                    metadata=metadata,
                )
            )
        return hits


def build_pinecone_store(settings: AppEnvironment) -> PineconeVectorStore:
    """Factory construct a PineconeVectorStore."""
    return PineconeVectorStore(settings=settings)
