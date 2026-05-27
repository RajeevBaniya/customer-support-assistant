from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.appEnvironment import AppEnvironment
from src.evaluation.models.benchmarkDatasetModel import BenchmarkDataset
from src.evaluation.repositories.benchmarkDatasetRepository import BenchmarkDatasetRepository
from src.models.userModel import User
from src.schemas.evaluationSchemas import BenchmarkDatasetCreate


class BenchmarkDatasetService:
    def __init__(self, session: AsyncSession, _settings: AppEnvironment) -> None:
        del _settings
        self._repo = BenchmarkDatasetRepository(session)

    @classmethod
    def from_request(
        cls,
        session: AsyncSession,
        settings: AppEnvironment,
    ) -> BenchmarkDatasetService:
        return cls(session, settings)

    async def create(self, *, user: User, payload: BenchmarkDatasetCreate) -> BenchmarkDataset:
        rows_dump: list[object] = [r.model_dump(mode="json") for r in payload.rows]
        self._repo.validate_rows(rows_dump)
        row = BenchmarkDataset(
            organization_id=user.organization_id,
            created_by_user_id=user.id,
            name=payload.name.strip(),
            rows=rows_dump,
        )
        return await self._repo.add(row)

    async def list_for_user(self, *, user: User, limit: int, offset: int) -> list[BenchmarkDataset]:
        return await self._repo.list_for_org(
            organization_id=user.organization_id,
            limit=limit,
            offset=offset,
        )

    async def get_for_user(self, dataset_id: UUID, *, user: User) -> BenchmarkDataset | None:
        return await self._repo.get_for_org(dataset_id, organization_id=user.organization_id)
