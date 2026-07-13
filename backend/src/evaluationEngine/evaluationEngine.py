from __future__ import annotations

from time import perf_counter

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.appEnvironment import AppEnvironment
from src.evaluation.repositories.benchmarkDatasetRepository import BenchmarkDatasetRepository
from src.evaluation.scoring.evaluationScoreBundle import compute_evaluation_scores
from src.evaluation.scoring.textSignals import truncate_context_text
from src.evaluationEngine.evaluationMetrics import (
    EvaluationDatasetMetrics,
    EvaluationQuestionMetrics,
)
from src.evaluationEngine.evaluationModels import EvaluationDatasetRequest, EvaluationRequest
from src.evaluationEngine.evaluationResult import EvaluationDatasetResult, EvaluationResult
from src.observability.structuredLogger import get_logger
from src.orchestration.workflowOrchestrator import WorkflowOrchestrator
from src.orchestration.workflowRequest import WorkflowRequest
from src.schemas.evaluationSchemas import BenchmarkDatasetRow
from src.shared.customExceptions import BaseApplicationException, ResourceNotFoundException

logger = get_logger("evaluation.engine")


class EvaluationEngine:
    """Execution boundary layer isolating evaluations and benchmark datasets workflows."""

    def __init__(self, session: AsyncSession, settings: AppEnvironment) -> None:
        self._session = session
        self._settings = settings
        self._orchestrator = WorkflowOrchestrator(session, settings)

    async def execute(
        self, request: EvaluationRequest, dataset_row_index: int | None = None
    ) -> EvaluationResult:
        """Executes a single ad-hoc evaluation workflow via WorkflowOrchestrator."""
        start_time = perf_counter()

        wf_req = WorkflowRequest(
            user_message=request.query,
            organization_id=request.organization_id,
            user_id=request.user_id,
            selected_document_ids=request.document_ids,
            stream=False,
            evaluation_mode=True,
        )

        try:
            wf_res = await self._orchestrator.execute(
                wf_req, prior_turns_text=request.prior_turns_text
            )
        except Exception as exc:
            if isinstance(exc, BaseApplicationException):
                raise
            raise BaseApplicationException(
                f"Evaluation pipeline execution failed: {str(exc)}",
                error_code="evaluation_execution_failed",
                status_code=500,
            ) from exc

        overall_latency = (perf_counter() - start_time) * 1000.0

        answer = wf_res.response_result.assistant_text
        chunks = wf_res.retrieval_result.retrieved_chunks if wf_res.retrieval_result else []
        context_text = "\n\n".join(c.text for c in chunks)
        retrieved_context = truncate_context_text(context_text)

        chunk_refs = [
            {
                "document_id": c.document_id,
                "chunk_index": c.chunk_index,
                "document_name": c.document_name,
                "similarity_score": c.similarity_score,
            }
            for c in chunks
        ]

        citations = [
            {
                "document_id": cite.document_id,
                "chunk_index": cite.chunk_index,
                "document_name": cite.document_name,
                "source_page": cite.source_page,
            }
            for cite in wf_res.response_result.citations
        ]

        top_k = (
            wf_res.retrieval_result.retrieval_metrics.top_k_used
            if (wf_res.retrieval_result and wf_res.retrieval_result.retrieval_metrics)
            else (request.top_k or self._settings.retrieval_default_top_k)
        )

        scores = compute_evaluation_scores(
            query=request.query,
            answer=answer,
            context=retrieved_context,
            chunk_refs=chunk_refs,
            citations_count=len(citations),
            top_k=top_k,
        )

        retrieval_latency = (
            wf_res.retrieval_result.retrieval_metrics.retrieval_latency_ms
            if (wf_res.retrieval_result and wf_res.retrieval_result.retrieval_metrics)
            else 0.0
        )
        generation_latency = (
            wf_res.generation_result.latency_ms if wf_res.generation_result else 0.0
        )

        metrics = EvaluationQuestionMetrics(
            provider_used=wf_res.response_result.provider_used,
            fallback_used=wf_res.response_result.fallback_used,
            retrieval_enabled=wf_res.execution_plan.retrieval.need_retrieval,
            retrieval_latency_ms=retrieval_latency,
            generation_latency_ms=generation_latency,
            overall_latency_ms=overall_latency,
        )

        return EvaluationResult(
            query=request.query,
            answer=answer,
            retrieved_context=retrieved_context,
            retrieved_chunk_refs=chunk_refs,
            citations=citations,
            scores=scores,
            provider=wf_res.response_result.provider_used,
            latency_ms=overall_latency,
            dataset_row_index=dataset_row_index,
            metrics=metrics,
        )

    async def execute_dataset(self, request: EvaluationDatasetRequest) -> EvaluationDatasetResult:
        """Runs a complete benchmark dataset evaluation using WorkflowOrchestrator."""
        start_dataset_time = perf_counter()

        ds_repo = BenchmarkDatasetRepository(self._session)
        ds = await ds_repo.get_for_org(request.dataset_id, organization_id=request.organization_id)
        if ds is None:
            raise ResourceNotFoundException(
                "Benchmark dataset not found",
                details={"dataset_id": str(request.dataset_id)},
            )

        rows_raw = ds.rows
        if not isinstance(rows_raw, list):
            raise BaseApplicationException(
                "Benchmark dataset rows are invalid",
                error_code="invalid_dataset_rows",
                status_code=400,
            )

        results: list[EvaluationResult] = []
        rows_total = len(rows_raw)
        rows_ok = 0
        rows_failed = 0

        for idx, raw in enumerate(rows_raw):
            if not isinstance(raw, dict):
                rows_failed += 1
                continue
            try:
                row = BenchmarkDatasetRow.model_validate(raw)
            except Exception:
                rows_failed += 1
                continue

            eval_req = EvaluationRequest(
                query=row.query,
                reference_answer=None,
                organization_id=request.organization_id,
                user_id=request.user_id,
                document_ids=row.document_ids,
                top_k=row.top_k,
                prior_turns_text=row.prior_turns_text,
            )

            try:
                res = await self.execute(eval_req, dataset_row_index=idx)
                results.append(res)
                rows_ok += 1
            except Exception as exc:
                rows_failed += 1
                logger.warning(
                    "evaluation_benchmark_row_failed",
                    dataset_id=str(request.dataset_id),
                    row_index=idx,
                    exc_type=type(exc).__name__,
                )

        dataset_duration = (perf_counter() - start_dataset_time) * 1000.0

        latencies = [res.latency_ms for res in results]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        total_chunks = sum(len(res.retrieved_chunk_refs) for res in results)
        total_fallbacks = sum(1 for res in results if res.metrics.fallback_used)

        provider_breakdown: dict[str, int] = {}
        for res in results:
            p = res.provider
            provider_breakdown[p] = provider_breakdown.get(p, 0) + 1

        if rows_failed == 0 and rows_ok > 0:
            status = "success"
        elif rows_ok > 0 and rows_failed > 0:
            status = "partial_success"
        else:
            status = "failed"

        dataset_metrics = EvaluationDatasetMetrics(
            dataset_execution_duration_ms=dataset_duration,
            per_question_latencies_ms=latencies,
            question_count=rows_total,
            successful_question_count=rows_ok,
            failed_question_count=rows_failed,
            average_question_latency_ms=avg_latency,
            total_retrieved_chunk_count=total_chunks,
            total_fallback_count=total_fallbacks,
            provider_usage_breakdown=provider_breakdown,
            execution_status=status,
        )

        summary = {
            "rows_total": rows_total,
            "rows_ok": rows_ok,
            "rows_failed": rows_failed,
        }

        return EvaluationDatasetResult(
            dataset_id=request.dataset_id,
            results=results,
            summary=summary,
            metrics=dataset_metrics,
        )
