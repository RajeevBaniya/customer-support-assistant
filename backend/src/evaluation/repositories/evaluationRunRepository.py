from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.evaluation.models.evaluationRunModel import EvaluationRun


class EvaluationRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, row: EvaluationRun) -> EvaluationRun:
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_for_org(self, run_id: UUID, *, organization_id: UUID) -> EvaluationRun | None:
        stmt = select(EvaluationRun).where(
            EvaluationRun.id == run_id,
            EvaluationRun.organization_id == organization_id,
        )
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_for_org(
        self,
        *,
        organization_id: UUID,
        limit: int,
        offset: int,
    ) -> list[EvaluationRun]:
        stmt = (
            select(EvaluationRun)
            .where(EvaluationRun.organization_id == organization_id)
            .order_by(EvaluationRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        res = await self._session.execute(stmt)
        return list(res.scalars().all())

    async def update_fields(
        self,
        run_id: UUID,
        *,
        organization_id: UUID,
        fields: dict[str, object],
    ) -> None:
        stmt = (
            update(EvaluationRun)
            .where(
                EvaluationRun.id == run_id,
                EvaluationRun.organization_id == organization_id,
            )
            .values(**fields)
        )
        await self._session.execute(stmt)
