from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.appEnvironment import AppEnvironment
from src.evaluation.evaluationConstants import evaluation_result_passes
from src.evaluation.models.evaluationResultModel import EvaluationResult as DbEvaluationResult
from src.evaluation.scoring.textSignals import build_retrieved_context, chunk_refs_from_state
from src.evaluationEngine.evaluationEngine import EvaluationEngine
from src.evaluationEngine.evaluationModels import EvaluationRequest
from src.jobs.evaluationTasks import enqueue_benchmark_evaluation
from src.models.userModel import User
from src.observability.structuredLogger import get_logger
from src.runtimeTools.evaluationTool import (
    CompleteRunRequest,
    CreateRunRequest,
    EvaluationTool,
    UpdateRunStatusRequest,
)
from src.runtimeTools.metricsTool import MetricsTool, RecordEvaluationRunRequest
from src.runtimeTools.retrieveTool import RetrieveTool
from src.schemas.evaluationSchemas import EvaluationRunRequest
from src.shared.customExceptions import ResourceNotFoundException
from src.workflows.state.chat_rag_state import ChatRagState

logger = get_logger(__name__)

RUN_SINGLE = "single"
RUN_BENCHMARK = "benchmark"
STATUS_QUEUED = "queued"
STATUS_PROCESSING = "processing"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"


class EvaluationRunService:
    """Service handling single and benchmark-scoped evaluation run logic."""

    def __init__(self, session: AsyncSession, settings: AppEnvironment) -> None:
        self._settings = settings
        self._evaluation_tool = EvaluationTool(session, settings)
        self._retrieve_tool = RetrieveTool(session, settings)
        self._metrics_tool = MetricsTool(session, settings)

    @classmethod
    def from_request(cls, session: AsyncSession, settings: AppEnvironment) -> EvaluationRunService:
        """Factory constructor."""
        return cls(session, settings)

    async def run_single_sync(
        self,
        *,
        user: User,
        req: EvaluationRunRequest,
    ) -> UUID:
        """Execute single ad-hoc evaluation workflow synchronously."""
        run = await self._evaluation_tool.create_run(
            CreateRunRequest(
                organization_id=user.organization_id,
                user_id=user.id,
                run_type=RUN_SINGLE,
                status=STATUS_PROCESSING,
            )
        )
        self._metrics_tool.record_evaluation(
            RecordEvaluationRunRequest(run_type=RUN_SINGLE, status=STATUS_PROCESSING)
        )
        logger.info("evaluation_run_started", run_id=str(run.id))

        engine = EvaluationEngine(self._evaluation_tool._session, self._settings)
        eval_req = EvaluationRequest(
            query=req.query,
            reference_answer=getattr(req, "reference_answer", None),
            organization_id=user.organization_id,
            user_id=user.id,
        )

        try:
            res = await engine.execute(eval_req)
        except Exception as exception:
            await self._mark_run_failed(run.id, user.organization_id, exception)
            raise

        latency_ms = int(res.latency_ms)
        scores = res.scores

        db_res = DbEvaluationResult(
            run_id=run.id,
            organization_id=user.organization_id,
            conversation_id=None,
            query=res.query,
            answer=res.answer,
            retrieved_context=res.retrieved_context,
            retrieved_chunk_refs=res.retrieved_chunk_refs,
            citations=res.citations,
            hallucination_score=scores["hallucination_score"],
            faithfulness_score=scores["faithfulness_score"],
            retrieval_relevance_score=scores["retrieval_relevance_score"],
            answer_relevance_score=scores["answer_relevance_score"],
            provider=res.provider,
            latency_ms=latency_ms,
            dataset_row_index=None,
        )

        await self._evaluation_tool.complete_run(
            CompleteRunRequest(
                run_id=run.id,
                organization_id=user.organization_id,
                fields={
                    "status": STATUS_COMPLETED,
                    "latency_ms": latency_ms,
                    "workflow_trace_summary": None,
                },
                results=[db_res],
            )
        )

        if not evaluation_result_passes(
            hallucination_score=float(scores["hallucination_score"]),
            faithfulness_score=float(scores["faithfulness_score"]),
        ):
            self._metrics_tool.record_hallucination()

        self._metrics_tool.record_evaluation(
            RecordEvaluationRunRequest(run_type=RUN_SINGLE, status=STATUS_COMPLETED)
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

    async def _mark_run_failed(
        self,
        run_id: UUID,
        organization_id: UUID,
        exception: Exception,
    ) -> None:
        """Mark the evaluation run as failed in database and observability records."""
        await self._evaluation_tool.update_run_status(
            UpdateRunStatusRequest(
                run_id=run_id,
                organization_id=organization_id,
                fields={"status": STATUS_FAILED},
            )
        )
        self._metrics_tool.record_evaluation(
            RecordEvaluationRunRequest(run_type=RUN_SINGLE, status=STATUS_FAILED)
        )
        logger.warning(
            "evaluation_run_failed",
            run_id=str(run_id),
            exc_type=type(exception).__name__,
        )

    def _build_evaluation_result(
        self,
        *,
        run_id: UUID,
        user: User,
        req: EvaluationRunRequest,
        evaluation_output: dict[str, Any],
        latency_ms: int,
    ) -> DbEvaluationResult:
        """Assemble DbEvaluationResult object from workflow output attributes."""
        rag_response = cast(dict[str, Any], evaluation_output["rag_response"])
        scores = cast(dict[str, float], evaluation_output["scores"])
        graph_pack = cast(dict[str, Any], evaluation_output["graph_pack"])
        graph_state = cast(
            ChatRagState,
            {
                "context_text": graph_pack.get("context_text"),
                "capped_items": graph_pack.get("capped_items") or [],
            },
        )
        retrieved_context = build_retrieved_context(graph_state)
        chunk_references = chunk_refs_from_state(graph_state)
        citations_json = list(rag_response.get("citations") or [])

        return DbEvaluationResult(
            run_id=run_id,
            organization_id=user.organization_id,
            conversation_id=None,
            query=req.query,
            answer=str(rag_response.get("answer") or ""),
            retrieved_context=retrieved_context,
            retrieved_chunk_refs=[dict(reference) for reference in chunk_references],
            citations=citations_json,
            hallucination_score=float(scores["hallucination_score"]),
            faithfulness_score=float(scores["faithfulness_score"]),
            retrieval_relevance_score=float(scores["retrieval_relevance_score"]),
            answer_relevance_score=float(scores["answer_relevance_score"]),
            provider=str(rag_response.get("provider") or "none"),
            latency_ms=latency_ms,
            dataset_row_index=None,
        )

    async def start_benchmark_run(self, *, user: User, dataset_id: UUID) -> UUID:
        """Queue a new benchmark dataset evaluation run."""
        dataset = await self._evaluation_tool.get_dataset(
            dataset_id,
            organization_id=user.organization_id,
        )
        if dataset is None:
            raise ResourceNotFoundException(
                "Benchmark dataset not found",
                details={"dataset_id": str(dataset_id)},
            )
        run = await self._evaluation_tool.create_run(
            CreateRunRequest(
                organization_id=user.organization_id,
                user_id=user.id,
                run_type=RUN_BENCHMARK,
                status=STATUS_QUEUED,
                benchmark_dataset_id=dataset_id,
            )
        )
        self._metrics_tool.record_evaluation(
            RecordEvaluationRunRequest(run_type=RUN_BENCHMARK, status=STATUS_QUEUED)
        )
        enqueue_benchmark_evaluation(
            run_id=run.id,
            organization_id=user.organization_id,
        )
        return run.id
