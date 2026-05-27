from __future__ import annotations

import json
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.evaluation.models.benchmarkDatasetModel import BenchmarkDataset
from src.schemas.evaluationSchemas import MAX_BENCHMARK_PAYLOAD_BYTES, MAX_BENCHMARK_ROWS


class BenchmarkDatasetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, row: BenchmarkDataset) -> BenchmarkDataset:
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_for_org(
        self,
        dataset_id: UUID,
        *,
        organization_id: UUID,
    ) -> BenchmarkDataset | None:
        stmt = select(BenchmarkDataset).where(
            BenchmarkDataset.id == dataset_id,
            BenchmarkDataset.organization_id == organization_id,
        )
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_for_org(
        self,
        *,
        organization_id: UUID,
        limit: int,
        offset: int,
    ) -> list[BenchmarkDataset]:
        stmt = (
            select(BenchmarkDataset)
            .where(BenchmarkDataset.organization_id == organization_id)
            .order_by(BenchmarkDataset.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        res = await self._session.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    def validate_rows(rows: Sequence[object]) -> None:
        if len(rows) > MAX_BENCHMARK_ROWS:
            raise ValueError("benchmark_rows_over_limit")
        size = len(json.dumps(rows, default=str).encode("utf-8"))
        if size > MAX_BENCHMARK_PAYLOAD_BYTES:
            raise ValueError("benchmark_payload_over_limit")
