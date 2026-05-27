from datetime import UTC, datetime
from time import perf_counter
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.appEnvironment import AppEnvironment
from src.documents.documentRepository import DocumentRepository
from src.observability.structuredLogger import get_logger
from src.retrieval.reranking import run_rerank_dedupe_pipeline
from src.retrieval.retrievalFilters import document_is_retrieval_ready, filter_scored_hits
from src.retrieval.retrievalMetadata import build_chunk_item
from src.retrieval.retrievalRanking import cosine_distance_to_similarity
from src.retrieval.semanticSearch import build_vector_store, run_vector_query
from src.schemas.retrievalSchemas import RetrievalSearchRequest, RetrievalSearchResponse
from src.shared.customExceptions import BaseApplicationException
from src.vectorstore.queryHit import VectorQueryHit

logger = get_logger(__name__)


class RetrievalService:
    def __init__(self, session: AsyncSession, settings: AppEnvironment) -> None:
        self._settings = settings
        self._documents = DocumentRepository(session)

    @classmethod
    def from_request(cls, session: AsyncSession, settings: AppEnvironment) -> "RetrievalService":
        return cls(session, settings)

    def _require_pinecone(self) -> None:
        if not self._settings.pinecone_configured():
            raise BaseApplicationException(
                "Semantic retrieval is not configured",
                error_code="retrieval_service_unavailable",
                status_code=503,
                details={"reason": "pinecone_not_configured"},
            )

    async def search(
        self,
        *,
        organization_id: UUID,
        body: RetrievalSearchRequest,
    ) -> RetrievalSearchResponse:
        self._require_pinecone()
        top_k = self._effective_top_k(body)
        if body.document_ids is not None and len(body.document_ids) == 0:
            return RetrievalSearchResponse(items=[], query=body.query, top_k=top_k)

        fetch_limit = self._settings.retrieval_max_top_k
        if body.document_ids is not None and len(body.document_ids) > 0:
            fetch_limit = min(256, fetch_limit * 4)

        store = build_vector_store(self._settings)
        t_req0 = perf_counter()
        try:
            raw_hits, vec_timings = await run_vector_query(
                settings=self._settings,
                store=store,
                organization_id=organization_id,
                query=body.query,
                fetch_limit=fetch_limit,
                document_ids=body.document_ids,
            )
        except Exception as exc:
            raise BaseApplicationException(
                "Semantic retrieval failed",
                error_code="retrieval_service_unavailable",
                status_code=503,
                details={"reason": str(exc)},
            ) from exc
        request_ms = round((perf_counter() - t_req0) * 1000.0, 3)

        scored = [(h, cosine_distance_to_similarity(h.distance)) for h in raw_hits]
        post_sim = filter_scored_hits(
            scored,
            minimum_similarity=self._settings.retrieval_minimum_similarity,
        )
        if not post_sim:
            logger.info(
                "retrieval_search",
                organization_id=str(organization_id),
                raw_hits=len(raw_hits),
                post_similarity_filter=0,
                post_ready_filter=0,
                rerank_input=0,
                post_dedup=0,
                near_dup_dropped=0,
                final_chunks=0,
                top_k=top_k,
                embed_ms=vec_timings["embed_ms"],
                pinecone_ms=vec_timings["pinecone_ms"],
                retrieval_request_ms=request_ms,
                rerank_ms=0.0,
            )
            return RetrievalSearchResponse(items=[], query=body.query, top_k=top_k)

        doc_ids = list({h.document_id for h, _ in post_sim})
        doc_map = await self._documents.map_by_ids_for_org(organization_id, doc_ids)

        ready: list[tuple[VectorQueryHit, float]] = []
        for hit, sim in post_sim:
            row = doc_map.get(hit.document_id)
            if not document_is_retrieval_ready(row):
                continue
            ready.append((hit, sim))

        now = datetime.now(UTC)
        pipe = run_rerank_dedupe_pipeline(
            ready,
            query=body.query.strip(),
            doc_map=doc_map,
            now=now,
        )
        trimmed = pipe.hits[:top_k]

        items = [
            build_chunk_item(hit=hit, similarity_score=sim, document=doc_map[hit.document_id])
            for hit, sim in trimmed
        ]

        logger.info(
            "retrieval_search",
            organization_id=str(organization_id),
            raw_hits=len(raw_hits),
            post_similarity_filter=len(post_sim),
            post_ready_filter=len(ready),
            rerank_input=pipe.rerank_input_count,
            post_dedup=pipe.after_dedup_count,
            near_dup_dropped=pipe.near_dup_dropped,
            final_chunks=len(items),
            top_k=top_k,
            embed_ms=vec_timings["embed_ms"],
            pinecone_ms=vec_timings["pinecone_ms"],
            retrieval_request_ms=request_ms,
            rerank_ms=pipe.rerank_ms,
        )
        return RetrievalSearchResponse(items=items, query=body.query, top_k=top_k)

    def _effective_top_k(self, body: RetrievalSearchRequest) -> int:
        cap = self._settings.retrieval_max_top_k
        default = min(self._settings.retrieval_default_top_k, cap)
        if body.top_k is None:
            return default
        return min(body.top_k, cap)
