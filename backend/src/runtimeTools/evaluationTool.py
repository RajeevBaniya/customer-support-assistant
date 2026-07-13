"""EvaluationTool wrapping evaluation runs and scoring results storage."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from src.evaluation.models.evaluationResultModel import EvaluationResult
from src.evaluation.models.evaluationRunModel import EvaluationRun
from src.evaluation.repositories.benchmarkDatasetRepository import (
    BenchmarkDatasetRepository,
)
from src.evaluation.repositories.evaluationRunRepository import EvaluationRunRepository
from src.runtimeTools.baseTool import BaseTool


class CreateRunRequest(BaseModel):
    """Schema for initializing an evaluation run."""

    organization_id: UUID
    user_id: UUID
    run_type: str = Field(min_length=1)
    status: str = Field(default="running", min_length=1)
    benchmark_dataset_id: UUID | None = None


class UpdateRunStatusRequest(BaseModel):
    """Schema for updating run status."""

    run_id: UUID
    organization_id: UUID
    fields: dict[str, Any]


class CompleteRunRequest(BaseModel):
    """Schema for completing run and saving results."""

    model_config = {"arbitrary_types_allowed": True}

    run_id: UUID
    organization_id: UUID
    fields: dict[str, Any]
    results: list[EvaluationResult] = Field(default_factory=list)


class EvaluationTool(BaseTool):
    """Evaluation runs and scoring results storage tool."""

    async def create_run(self, request: CreateRunRequest) -> EvaluationRun:
        """Store a new evaluation run context."""
        repository = EvaluationRunRepository(self._session)
        run = EvaluationRun(
            organization_id=request.organization_id,
            user_id=request.user_id,
            run_type=request.run_type,
            status=request.status,
            benchmark_dataset_id=request.benchmark_dataset_id,
        )
        return await repository.add(run)

    async def update_run_status(self, request: UpdateRunStatusRequest) -> None:
        """Update status parameters of a run."""
        repository = EvaluationRunRepository(self._session)
        await repository.update_fields(
            request.run_id,
            organization_id=request.organization_id,
            fields=request.fields,
        )

    async def complete_run(self, request: CompleteRunRequest) -> None:
        """Save evaluation results and complete the run."""
        repository = EvaluationRunRepository(self._session)
        await repository.update_fields(
            request.run_id,
            organization_id=request.organization_id,
            fields=request.fields,
        )
        for result in request.results:
            self._session.add(result)
        await self._session.flush()

    async def get_dataset(
        self, dataset_id: UUID, organization_id: UUID
    ) -> Any | None:
        """Retrieve benchmark dataset details."""
        repository = BenchmarkDatasetRepository(self._session)
        return await repository.get_for_org(dataset_id, organization_id=organization_id)

