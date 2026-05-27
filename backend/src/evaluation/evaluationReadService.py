from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.appEnvironment import AppEnvironment
from src.evaluation.models.evaluationResultModel import EvaluationResult
from src.evaluation.repositories.evaluationResultRepository import EvaluationResultRepository
from src.evaluation.repositories.evaluationRunRepository import EvaluationRunRepository
from src.models.userModel import User
from src.schemas.evaluationSchemas import (
    EvaluationResultOut,
    EvaluationRunDetail,
    EvaluationRunSummary,
)
from src.shared.customExceptions import ResourceNotFoundException


class EvaluationReadService:
    def __init__(self, session: AsyncSession, _settings: AppEnvironment) -> None:
        del _settings
        self._runs = EvaluationRunRepository(session)
        self._results = EvaluationResultRepository(session)

    @classmethod
    def from_request(cls, session: AsyncSession, settings: AppEnvironment) -> EvaluationReadService:
        return cls(session, settings)

    async def list_runs(self, *, user: User, limit: int, offset: int) -> list[EvaluationRunSummary]:
        rows = await self._runs.list_for_org(
            organization_id=user.organization_id,
            limit=limit,
            offset=offset,
        )
        return [
            EvaluationRunSummary(
                id=r.id,
                run_type=r.run_type,
                status=r.status,
                latency_ms=r.latency_ms,
                created_at=r.created_at,
            )
            for r in rows
        ]

    async def get_run_detail(self, *, user: User, run_id: UUID) -> EvaluationRunDetail:
        run = await self._runs.get_for_org(run_id, organization_id=user.organization_id)
        if run is None:
            raise ResourceNotFoundException(
                "Evaluation run not found",
                details={"run_id": str(run_id)},
            )
        res_rows = await self._results.list_for_run(
            run_id,
            organization_id=user.organization_id,
        )
        results = [_map_result(r) for r in res_rows]
        return EvaluationRunDetail(
            id=run.id,
            run_type=run.run_type,
            status=run.status,
            latency_ms=run.latency_ms,
            error_message=run.error_message,
            workflow_trace_summary=run.workflow_trace_summary,
            created_at=run.created_at,
            results=results,
        )


def _map_result(row: EvaluationResult) -> EvaluationResultOut:
    return EvaluationResultOut(
        id=row.id,
        query=row.query,
        answer=row.answer,
        hallucination_score=row.hallucination_score,
        faithfulness_score=row.faithfulness_score,
        retrieval_relevance_score=row.retrieval_relevance_score,
        answer_relevance_score=row.answer_relevance_score,
        provider=row.provider,
        latency_ms=row.latency_ms,
    )
