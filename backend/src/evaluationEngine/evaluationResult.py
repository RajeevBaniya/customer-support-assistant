from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from src.evaluationEngine.evaluationMetrics import (
    EvaluationDatasetMetrics,
    EvaluationQuestionMetrics,
)


class EvaluationResult(BaseModel):
    model_config = {"frozen": True}

    query: str
    answer: str
    retrieved_context: str
    retrieved_chunk_refs: list[dict[str, object]]
    citations: list[dict[str, object]]
    scores: dict[str, float]
    provider: str
    latency_ms: float
    dataset_row_index: int | None = None
    metrics: EvaluationQuestionMetrics

class EvaluationDatasetResult(BaseModel):
    model_config = {"frozen": True}

    dataset_id: UUID
    results: list[EvaluationResult]
    summary: dict[str, int]
    metrics: EvaluationDatasetMetrics
