from __future__ import annotations

import asyncio
from uuid import UUID

from celery import Task

from src.core.appEnvironment import get_app_environment
from src.database.databaseSession import session_scope
from src.evaluation.evaluationConstants import STATUS_COMPLETED, STATUS_FAILED, STATUS_RUNNING
from src.evaluation.models.evaluationResultModel import EvaluationResult as DbEvaluationResult
from src.evaluation.repositories.evaluationResultRepository import EvaluationResultRepository
from src.evaluation.repositories.evaluationRunRepository import EvaluationRunRepository
from src.evaluationEngine.evaluationEngine import EvaluationEngine
from src.evaluationEngine.evaluationModels import EvaluationDatasetRequest
from src.jobs.celeryApp import celery_app
from src.observability.structuredLogger import get_logger

logger = get_logger(__name__)


def enqueue_benchmark_evaluation(*, run_id: UUID, organization_id: UUID) -> None:
    run_benchmark_evaluation_task.delay(str(run_id), str(organization_id))


@celery_app.task(bind=True, name="recallstack.evaluation.benchmark_run")  # type: ignore[misc]
def run_benchmark_evaluation_task(self: Task, run_id: str, organization_id: str) -> None:
    del self
    rid = UUID(run_id)
    oid = UUID(organization_id)

    async def _run() -> None:
        settings = get_app_environment()

        # 1. Read dataset and initialize status (short-lived DB session)
        async with session_scope() as session:
            runs = EvaluationRunRepository(session)
            run_row = await runs.get_for_org(rid, organization_id=oid)
            if run_row is None or run_row.benchmark_dataset_id is None:
                logger.warning("evaluation_benchmark_missing_run", run_id=run_id)
                return
            await runs.update_fields(
                rid,
                organization_id=oid,
                fields={"status": STATUS_RUNNING},
            )

        # 2. Run benchmark evaluation via EvaluationEngine
        try:
            async with session_scope() as session:
                engine = EvaluationEngine(session, settings)
                dataset_req = EvaluationDatasetRequest(
                    dataset_id=run_row.benchmark_dataset_id,
                    organization_id=oid,
                    user_id=run_row.user_id,
                )
                dataset_res = await engine.execute_dataset(dataset_req)
        except Exception as exc:
            logger.error("evaluation_benchmark_failed", run_id=run_id, exc=str(exc))
            async with session_scope() as session:
                runs = EvaluationRunRepository(session)
                await runs.update_fields(
                    rid,
                    organization_id=oid,
                    fields={"status": STATUS_FAILED, "error_message": str(exc)},
                )
            return

        # 3. Store results in the database (short-lived DB session)
        async with session_scope() as session:
            results_repo = EvaluationResultRepository(session)
            for res in dataset_res.results:
                er = DbEvaluationResult(
                    run_id=rid,
                    organization_id=oid,
                    conversation_id=None,
                    query=res.query,
                    answer=res.answer,
                    retrieved_context=res.retrieved_context,
                    retrieved_chunk_refs=res.retrieved_chunk_refs,
                    citations=res.citations,
                    hallucination_score=res.scores["hallucination_score"],
                    faithfulness_score=res.scores["faithfulness_score"],
                    retrieval_relevance_score=res.scores["retrieval_relevance_score"],
                    answer_relevance_score=res.scores["answer_relevance_score"],
                    provider=res.provider,
                    latency_ms=int(res.latency_ms),
                    dataset_row_index=res.dataset_row_index,
                )
                await results_repo.add(er)

        # 4. Save final benchmark stats (short-lived DB session)
        wall_ms = int(dataset_res.metrics.dataset_execution_duration_ms)
        async with session_scope() as session:
            runs = EvaluationRunRepository(session)
            await runs.update_fields(
                rid,
                organization_id=oid,
                fields={
                    "status": STATUS_COMPLETED,
                    "latency_ms": wall_ms,
                    "workflow_trace_summary": dataset_res.summary,
                },
            )
        logger.info(
            "evaluation_benchmark_completed",
            run_id=run_id,
            latency_ms=wall_ms,
            rows_ok=dataset_res.summary["rows_ok"],
            rows_failed=dataset_res.summary["rows_failed"],
        )

    asyncio.run(_run())
