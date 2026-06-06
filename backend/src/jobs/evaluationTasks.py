from __future__ import annotations

import asyncio
from time import perf_counter
from typing import Any, cast
from uuid import UUID

from celery import Task

from src.ai.ragService import RagService
from src.core.appEnvironment import get_app_environment
from src.database.databaseSession import session_scope
from src.evaluation.evaluationConstants import STATUS_COMPLETED, STATUS_FAILED, STATUS_RUNNING
from src.evaluation.models.evaluationResultModel import EvaluationResult
from src.evaluation.pipelines.evaluation_graph_runner import run_evaluation_graph_pass
from src.evaluation.repositories.benchmarkDatasetRepository import BenchmarkDatasetRepository
from src.evaluation.repositories.evaluationResultRepository import EvaluationResultRepository
from src.evaluation.repositories.evaluationRunRepository import EvaluationRunRepository
from src.evaluation.scoring.textSignals import build_retrieved_context, chunk_refs_from_state
from src.jobs.celeryApp import celery_app
from src.observability.structuredLogger import get_logger
from src.schemas.evaluationSchemas import BenchmarkDatasetRow
from src.schemas.retrievalSchemas import RetrievalSearchRequest
from src.workflows.state.chat_rag_state import ChatRagState

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
        t_wall = perf_counter()
        # 1. Read dataset and initialize state (short-lived DB session)
        rows_raw = None
        async with session_scope() as session:
            runs = EvaluationRunRepository(session)
            ds_repo = BenchmarkDatasetRepository(session)
            run_row = await runs.get_for_org(rid, organization_id=oid)
            if run_row is None or run_row.benchmark_dataset_id is None:
                logger.warning("evaluation_benchmark_missing_run", run_id=run_id)
                return
            await runs.update_fields(
                rid,
                organization_id=oid,
                fields={"status": STATUS_RUNNING},
            )
            ds = await ds_repo.get_for_org(run_row.benchmark_dataset_id, organization_id=oid)
            if ds is None:
                await runs.update_fields(
                    rid,
                    organization_id=oid,
                    fields={"status": STATUS_FAILED, "error_message": "dataset_missing"},
                )
                return
            rows_raw = ds.rows
            if not isinstance(rows_raw, list):
                await runs.update_fields(
                    rid,
                    organization_id=oid,
                    fields={"status": STATUS_FAILED, "error_message": "dataset_rows_invalid"},
                )
                return

        # 2. Instantiate RagService outside main transaction
        async with session_scope() as session:
            rag = RagService.from_request(session, settings)

        # 3. Process each row sequentially without holding active transactions
        summary: dict[str, Any] = {"rows_total": len(rows_raw), "rows_ok": 0, "rows_failed": 0}
        for idx, raw in enumerate(rows_raw):
            if not isinstance(raw, dict):
                summary["rows_failed"] += 1
                continue
            try:
                row = BenchmarkDatasetRow.model_validate(raw)
            except Exception:
                summary["rows_failed"] += 1
                continue
            body = RetrievalSearchRequest(
                query=row.query,
                top_k=row.top_k,
                document_ids=row.document_ids,
            )
            t0 = perf_counter()
            try:
                out = await run_evaluation_graph_pass(
                    rag=rag,
                    organization_id=oid,
                    body=body,
                    prior_turns_text=row.prior_turns_text,
                )
            except Exception as exc:
                summary["rows_failed"] += 1
                logger.warning(
                    "evaluation_benchmark_row_failed",
                    run_id=run_id,
                    row_index=idx,
                    exc_type=type(exc).__name__,
                )
                continue
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

            # Write row result (short-lived DB session)
            async with session_scope() as session:
                results = EvaluationResultRepository(session)
                er = EvaluationResult(
                    run_id=rid,
                    organization_id=oid,
                    conversation_id=None,
                    query=row.query,
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
                    dataset_row_index=idx,
                )
                await results.add(er)
            summary["rows_ok"] += 1

        # 4. Save final benchmark stats (short-lived DB session)
        wall_ms = int((perf_counter() - t_wall) * 1000.0)
        async with session_scope() as session:
            runs = EvaluationRunRepository(session)
            await runs.update_fields(
                rid,
                organization_id=oid,
                fields={
                    "status": STATUS_COMPLETED,
                    "latency_ms": wall_ms,
                    "workflow_trace_summary": summary,
                },
            )
        logger.info(
            "evaluation_benchmark_completed",
            run_id=run_id,
            latency_ms=wall_ms,
            rows_ok=summary["rows_ok"],
            rows_failed=summary["rows_failed"],
        )

    asyncio.run(_run())
