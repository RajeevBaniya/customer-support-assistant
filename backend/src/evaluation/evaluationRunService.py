from __future__ import annotations

from time import perf_counter
from typing import Any, cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.ragService import RagService
from src.core.appEnvironment import AppEnvironment
from src.evaluation.evaluationConstants import (
    RUN_BENCHMARK,
    RUN_SINGLE,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_QUEUED,
    STATUS_RUNNING,
)
from src.evaluation.models.evaluationResultModel import EvaluationResult
from src.evaluation.models.evaluationRunModel import EvaluationRun
from src.evaluation.pipelines.evaluation_graph_runner import run_evaluation_graph_pass
from src.evaluation.repositories.benchmarkDatasetRepository import BenchmarkDatasetRepository
from src.evaluation.repositories.evaluationResultRepository import EvaluationResultRepository
from src.evaluation.repositories.evaluationRunRepository import EvaluationRunRepository
from src.evaluation.scoring.textSignals import build_retrieved_context, chunk_refs_from_state
from src.jobs.evaluationTasks import enqueue_benchmark_evaluation
from src.models.userModel import User
from src.observability.structuredLogger import get_logger
from src.schemas.evaluationSchemas import EvaluationRunRequest
from src.schemas.retrievalSchemas import RetrievalSearchRequest
from src.shared.customExceptions import ResourceNotFoundException
from src.workflows.state.chat_rag_state import ChatRagState

logger = get_logger(__name__)


class EvaluationRunService:
    def __init__(self, session: AsyncSession, settings: AppEnvironment) -> None:
        self._session = session
        self._settings = settings
        self._runs = EvaluationRunRepository(session)
        self._results = EvaluationResultRepository(session)

    @classmethod
    def from_request(cls, session: AsyncSession, settings: AppEnvironment) -> EvaluationRunService:
        return cls(session, settings)

    async def run_single_sync(self, *, user: User, req: EvaluationRunRequest) -> UUID:
        body = RetrievalSearchRequest(
            query=req.query,
            top_k=req.top_k,
            document_ids=req.document_ids,
        )
        run = EvaluationRun(
            organization_id=user.organization_id,
            user_id=user.id,
            run_type=RUN_SINGLE,
            status=STATUS_RUNNING,
            benchmark_dataset_id=None,
            workflow_trace_summary=None,
            latency_ms=None,
            error_message=None,
        )
        await self._runs.add(run)
        rag = RagService.from_request(self._session, self._settings)
        t0 = perf_counter()
        try:
            out = await run_evaluation_graph_pass(
                rag=rag,
                organization_id=user.organization_id,
                body=body,
                prior_turns_text=req.prior_turns_text,
            )
        except Exception as exc:
            await self._runs.update_fields(
                run.id,
                organization_id=user.organization_id,
                fields={"status": STATUS_FAILED, "error_message": str(exc)[:8000]},
            )
            logger.warning(
                "evaluation_run_failed",
                run_id=str(run.id),
                exc_type=type(exc).__name__,
            )
            raise

        latency_ms = int((perf_counter() - t0) * 1000.0)
        resp = cast(dict[str, Any], out["rag_response"])
        scores = cast(dict[str, float], out["scores"])
        pack = cast(dict[str, Any], out["graph_pack"])
        gst = cast(
            ChatRagState,
            {
                "context_text": pack.get("context_text"),
                "capped_items": pack.get("capped_items") or [],
            },
        )
        ctx = build_retrieved_context(gst)
        refs = chunk_refs_from_state(gst)
        citations_json = list(resp.get("citations") or [])

        result = EvaluationResult(
            run_id=run.id,
            organization_id=user.organization_id,
            conversation_id=None,
            query=req.query,
            answer=str(resp.get("answer") or ""),
            retrieved_context=ctx,
            retrieved_chunk_refs=[dict(r) for r in refs],
            citations=citations_json,
            hallucination_score=float(scores["hallucination_score"]),
            faithfulness_score=float(scores["faithfulness_score"]),
            retrieval_relevance_score=float(scores["retrieval_relevance_score"]),
            answer_relevance_score=float(scores["answer_relevance_score"]),
            provider=str(resp.get("provider") or "none"),
            latency_ms=latency_ms,
            dataset_row_index=None,
        )
        await self._results.add(result)
        await self._runs.update_fields(
            run.id,
            organization_id=user.organization_id,
            fields={
                "status": STATUS_COMPLETED,
                "latency_ms": latency_ms,
                "workflow_trace_summary": out.get("workflow_trace_summary"),
            },
        )
        logger.info(
            "evaluation_run_completed",
            run_id=str(run.id),
            latency_ms=latency_ms,
            hallucination_score=scores["hallucination_score"],
            faithfulness_score=scores["faithfulness_score"],
            retrieval_relevance_score=scores["retrieval_relevance_score"],
            answer_relevance_score=scores["answer_relevance_score"],
        )
        return run.id

    async def start_benchmark_run(self, *, user: User, dataset_id: UUID) -> UUID:
        ds_repo = BenchmarkDatasetRepository(self._session)
        ds = await ds_repo.get_for_org(dataset_id, organization_id=user.organization_id)
        if ds is None:
            raise ResourceNotFoundException(
                "Benchmark dataset not found",
                details={"dataset_id": str(dataset_id)},
            )
        del ds
        run = EvaluationRun(
            organization_id=user.organization_id,
            user_id=user.id,
            run_type=RUN_BENCHMARK,
            status=STATUS_QUEUED,
            benchmark_dataset_id=dataset_id,
            workflow_trace_summary=None,
            latency_ms=None,
            error_message=None,
        )
        await self._runs.add(run)
        enqueue_benchmark_evaluation(
            run_id=run.id,
            organization_id=user.organization_id,
        )
        logger.info("evaluation_benchmark_queued", run_id=str(run.id), dataset_id=str(dataset_id))
        return run.id
