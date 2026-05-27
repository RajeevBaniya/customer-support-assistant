from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.evaluation.models.evaluationResultModel import EvaluationResult


class EvaluationResultRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, row: EvaluationResult) -> EvaluationResult:
        self._session.add(row)
        await self._session.flush()
        return row

    async def list_for_run(
        self,
        run_id: UUID,
        *,
        organization_id: UUID,
    ) -> list[EvaluationResult]:
        stmt = (
            select(EvaluationResult)
            .where(
                EvaluationResult.run_id == run_id,
                EvaluationResult.organization_id == organization_id,
            )
            .order_by(EvaluationResult.created_at.asc())
        )
        res = await self._session.execute(stmt)
        return list(res.scalars().all())
