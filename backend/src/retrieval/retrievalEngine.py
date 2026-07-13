from __future__ import annotations

from time import perf_counter
from typing import TYPE_CHECKING

from src.ai.citationBuilder import citations_from_chunks
from src.core.appEnvironment import AppEnvironment
from src.observability.structuredLogger import get_logger
from src.retrieval.retrievalMetrics import RetrievalMetrics
from src.retrieval.retrievalModels import RetrievalRequest
from src.retrieval.retrievalResult import RetrievalResult
from src.shared.customExceptions import BaseApplicationException

if TYPE_CHECKING:
    from src.observability.observabilityEngine import ObservabilityEngine
    from src.runtimeTools.retrieveTool import RetrieveTool

logger = get_logger("retrieval.engine")


class RetrievalEngine:
    """Execution boundary layer isolating vector store queries and result scoping."""

    def __init__(
        self,
        tool: RetrieveTool,
        settings: AppEnvironment,
        observability: ObservabilityEngine | None = None,
    ) -> None:
        self._tool = tool
        self._settings = settings
        self._observability = observability

    async def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        """Executes semantic search over target document scope."""
        start_time = perf_counter()

        plan = request.execution_plan
        context = request.runtime_context

        # 1. Deterministic bypass if planning determines retrieval is not needed
        if not plan.retrieval.need_retrieval:
            empty_metrics = RetrievalMetrics(
                retrieval_latency_ms=0.0,
                returned_chunk_count=0,
                filtered_chunk_count=0,
                top_k_used=0,
                retrieval_mode="none",
            )
            return RetrievalResult(
                retrieved_chunks=[],
                scores=[],
                citations=[],
                metadata={},
                retrieval_metrics=empty_metrics,
            )

        # 2. Scoped document limits resolution
        doc_ids = None
        if plan.retrieval.metadata_filter:
            doc_ids = plan.retrieval.metadata_filter.document_ids

        if not doc_ids and context.workspace.selected_documents:
            doc_ids = [doc.id for doc in context.workspace.selected_documents]

        # 3. Top-k and retrieval mode extraction
        top_k = (
            request.top_k
            or context.execution.top_k
            or self._settings.retrieval_default_top_k
        )
        retrieval_mode = (
            request.retrieval_mode
            or plan.retrieval.retrieval_mode
            or "semantic"
        )

        try:
            from src.runtimeTools.retrieveTool import RetrieveRequest

            retrieve_req = RetrieveRequest(
                query=request.query,
                organization_id=request.organization_id,
                document_ids=doc_ids,
                top_k=top_k,
            )
            search_response = await self._tool.retrieve(retrieve_req)
        except BaseApplicationException:
            raise
        except Exception as exc:
            raise BaseApplicationException(
                f"Vector store search failed: {str(exc)}",
                error_code="retrieval_failed",
                status_code=502,
                details={"reason": str(exc)},
            ) from exc

        duration_ms = (perf_counter() - start_time) * 1000.0
        citations = citations_from_chunks(search_response.items)

        metrics = RetrievalMetrics(
            retrieval_latency_ms=duration_ms,
            returned_chunk_count=len(search_response.items),
            filtered_chunk_count=0,
            top_k_used=top_k,
            retrieval_mode=retrieval_mode,
        )

        if self._observability:
            self._observability.start_stage("retrieval")
            self._observability.record_retrieval(
                returned_chunks=len(search_response.items),
                top_k=top_k,
                latency_ms=duration_ms,
                retrieval_mode=retrieval_mode,
                organization_id=request.organization_id,
            )
            self._observability.end_stage("retrieval", status="success")

        return RetrievalResult(
            retrieved_chunks=search_response.items,
            scores=[item.similarity_score for item in search_response.items],
            citations=citations,
            metadata={"query": request.query},
            retrieval_metrics=metrics,
        )
