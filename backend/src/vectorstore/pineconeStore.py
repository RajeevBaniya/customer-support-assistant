from typing import Any
from uuid import UUID

from pinecone import Pinecone

from src.core.appEnvironment import AppEnvironment
from src.vectorstore.queryHit import VectorQueryHit
from src.vectorstore.vectorStore import VectorStore


class PineconeVectorStore(VectorStore):
    def __init__(self, *, settings: AppEnvironment) -> None:
        key = (settings.pinecone_api_key or "").strip()
        name = (settings.pinecone_index_name or "").strip()
        if not key or not name:
            raise ValueError("pinecone_not_configured")
        pc = Pinecone(api_key=key)
        pc.indexes.describe(name)
        self._index = pc.Index(name)

    def upsert_chunks(
        self,
        *,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        step = 100
        for i in range(0, len(ids), step):
            batch: list[dict[str, Any]] = []
            for j in range(i, min(i + step, len(ids))):
                meta = dict(metadatas[j])
                meta["chunk_text"] = documents[j][:39000]
                batch.append({"id": ids[j], "values": embeddings[j], "metadata": meta})
            self._index.upsert(vectors=batch, show_progress=False)

    def delete_document_vectors(self, *, organization_id: str, document_id: str) -> None:
        flt: dict[str, Any] = {
            "organization_id": {"$eq": organization_id},
            "document_id": {"$eq": document_id},
        }
        self._index.delete(filter=flt)

    def semantic_search(
        self,
        *,
        query_embedding: list[float],
        organization_id: str,
        limit: int,
        document_ids: list[str] | None,
    ) -> list[VectorQueryHit]:
        flt: dict[str, Any] = {"organization_id": {"$eq": organization_id}}
        n_results = max(1, min(limit, 256))
        raw = self._index.query(
            top_k=n_results,
            vector=query_embedding,
            filter=flt,
            include_metadata=True,
        )
        matches = getattr(raw, "matches", None) or []
        hits: list[VectorQueryHit] = []
        for m in matches:
            meta_raw = getattr(m, "metadata", None) or {}
            meta = dict(meta_raw) if isinstance(meta_raw, dict) else {}
            doc_raw = meta.get("document_id")
            if not doc_raw:
                continue
            try:
                doc_id = UUID(str(doc_raw))
            except ValueError:
                continue
            chunk_raw = meta.get("chunk_index", 0)
            try:
                chunk_idx = int(chunk_raw)
            except (TypeError, ValueError):
                chunk_idx = 0
            score = float(getattr(m, "score", 0.0) or 0.0)
            dist = 1.0 - score
            vid = str(getattr(m, "id", "") or "")
            text = str(meta.get("chunk_text", ""))
            hits.append(
                VectorQueryHit(
                    vector_id=vid,
                    document_id=doc_id,
                    chunk_index=chunk_idx,
                    distance=dist,
                    text=text,
                    metadata=meta,
                )
            )
        if document_ids:
            allowed = set(document_ids)
            hits = [h for h in hits if str(h.document_id) in allowed]
        return hits


def build_pinecone_store(settings: AppEnvironment) -> PineconeVectorStore:
    return PineconeVectorStore(settings=settings)
