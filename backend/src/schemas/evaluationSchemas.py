from datetime import datetime
from uuid import UUID

from pydantic import Field

from src.schemas.commonSchemas import ApiModel

MAX_BENCHMARK_ROWS = 1000
MAX_BENCHMARK_PAYLOAD_BYTES = 5 * 1024 * 1024
MAX_RETRIEVED_CONTEXT_CHARS = 12000
MAX_WORKFLOW_TRACE_SUMMARY_CHARS = 8000


class BenchmarkDatasetRow(ApiModel):
    query: str = Field(min_length=3, max_length=2000)
    top_k: int | None = Field(default=None, ge=1, le=50)
    document_ids: list[UUID] | None = None
    prior_turns_text: str | None = Field(default=None, max_length=32000)


class BenchmarkDatasetCreate(ApiModel):
    name: str = Field(min_length=1, max_length=255)
    rows: list[BenchmarkDatasetRow] = Field(min_length=1)


class EvaluationRunRequest(ApiModel):
    query: str = Field(min_length=3, max_length=2000)
    top_k: int | None = Field(default=None, ge=1, le=50)
    document_ids: list[UUID] | None = None
    prior_turns_text: str | None = Field(default=None, max_length=32000)


class EvaluationRunQueuedResponse(ApiModel):
    run_id: UUID
    status: str


class BenchmarkDatasetResponse(ApiModel):
    id: UUID
    name: str
    row_count: int


class EvaluationRunSummary(ApiModel):
    id: UUID
    run_type: str
    status: str
    latency_ms: int | None
    created_at: datetime


class EvaluationResultOut(ApiModel):
    id: UUID
    query: str
    answer: str
    hallucination_score: float
    faithfulness_score: float
    retrieval_relevance_score: float
    answer_relevance_score: float
    provider: str
    latency_ms: int


class EvaluationRunDetail(ApiModel):
    id: UUID
    run_type: str
    status: str
    latency_ms: int | None
    error_message: str | None
    workflow_trace_summary: dict[str, object] | None
    created_at: datetime
    results: list[EvaluationResultOut]
