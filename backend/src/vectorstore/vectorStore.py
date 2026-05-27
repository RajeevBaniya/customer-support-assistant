from typing import Any, Protocol, runtime_checkable

from src.vectorstore.queryHit import VectorQueryHit


@runtime_checkable
class VectorStore(Protocol):
    def upsert_chunks(
        self,
        *,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        """Persist dense vectors with aligned ids, documents, and metadata rows."""

    def delete_document_vectors(self, *, organization_id: str, document_id: str) -> None:
        """Remove all vectors for one document within an organization."""

    def semantic_search(
        self,
        *,
        query_embedding: list[float],
        organization_id: str,
        limit: int,
        document_ids: list[str] | None,
    ) -> list[VectorQueryHit]:
        """Cosine-indexed similarity search scoped to one organization."""
