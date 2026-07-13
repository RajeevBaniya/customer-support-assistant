from __future__ import annotations

from pydantic import BaseModel


class EvaluationQuestionMetrics(BaseModel):
    model_config = {"frozen": True}

    provider_used: str
    fallback_used: bool
    retrieval_enabled: bool
    retrieval_latency_ms: float
    generation_latency_ms: float
    overall_latency_ms: float

class EvaluationDatasetMetrics(BaseModel):
    model_config = {"frozen": True}

    dataset_execution_duration_ms: float
    per_question_latencies_ms: list[float]
    question_count: int
    successful_question_count: int
    failed_question_count: int
    average_question_latency_ms: float
    total_retrieved_chunk_count: int
    total_fallback_count: int
    provider_usage_breakdown: dict[str, int]
    execution_status: str
