from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.evaluation.models.evaluationResultModel import EvaluationResult
from src.evaluation.models.evaluationRunModel import EvaluationRun
from src.models.ingestionJobModel import IngestionJob


class EvaluationAnalyticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def results_since(
        self,
        *,
        organization_id: UUID,
        since: datetime,
    ) -> list[EvaluationResult]:
        stmt = (
            select(EvaluationResult)
            .where(
                EvaluationResult.organization_id == organization_id,
                EvaluationResult.created_at >= since,
            )
            .order_by(EvaluationResult.created_at.desc())
        )
        res = await self._session.execute(stmt)
        return list(res.scalars().all())

    async def benchmark_runs_since(
        self,
        *,
        organization_id: UUID,
        since: datetime,
    ) -> list[EvaluationRun]:
        stmt = (
            select(EvaluationRun)
            .where(
                EvaluationRun.organization_id == organization_id,
                EvaluationRun.run_type == "benchmark",
                EvaluationRun.created_at >= since,
            )
            .order_by(EvaluationRun.created_at.desc())
        )
        res = await self._session.execute(stmt)
        return list(res.scalars().all())


class IngestionAnalyticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def jobs_since(
        self,
        *,
        organization_id: UUID,
        since: datetime,
    ) -> list[IngestionJob]:
        stmt = (
            select(IngestionJob)
            .where(
                IngestionJob.organization_id == organization_id,
                IngestionJob.created_at >= since,
            )
            .order_by(IngestionJob.created_at.desc())
        )
        res = await self._session.execute(stmt)
        return list(res.scalars().all())

    async def count_by_status(
        self,
        *,
        organization_id: UUID,
        since: datetime,
    ) -> dict[str, int]:
        stmt = (
            select(IngestionJob.status, func.count())
            .where(
                IngestionJob.organization_id == organization_id,
                IngestionJob.created_at >= since,
            )
            .group_by(IngestionJob.status)
        )
        res = await self._session.execute(stmt)
        return {str(row[0]): int(row[1]) for row in res.all()}


def since_from_hours(hours: int) -> datetime:
    return datetime.now(UTC) - timedelta(hours=hours)
