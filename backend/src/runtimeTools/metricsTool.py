"""MetricsTool exposing observability recording capabilities."""

from uuid import UUID

from pydantic import BaseModel, Field

from src.ai.generationUsage import GenerationUsage
from src.observability.metrics import recorders
from src.runtimeTools.baseTool import BaseTool


class RecordChatRequest(BaseModel):
    """Schema for chat operation metrics."""

    mode: str = Field(min_length=1)


class RecordRetrievalRequest(BaseModel):
    """Schema for retrieval quality and performance metrics."""

    organization_id: UUID | None = None
    duration_seconds: float = Field(ge=0.0)
    final_chunks: int = Field(ge=0)
    avg_similarity: float = Field(ge=0.0)
    rerank_input: int = Field(ge=0)
    post_dedup: int = Field(ge=0)
    near_dup_dropped: int = Field(ge=0)
    top_k: int = Field(ge=1)


class RecordGenerationUsageRequest(BaseModel):
    """Schema for LLM token usage tracking metrics."""

    model_config = {"arbitrary_types_allowed": True}

    organization_id: UUID | None = None
    provider: str = Field(min_length=1)
    route_type: str = Field(min_length=1)
    usage: GenerationUsage


class RecordEvaluationRunRequest(BaseModel):
    """Schema for evaluation run statuses."""

    run_type: str = Field(min_length=1)
    status: str = Field(min_length=1)


class RecordIngestionJobRequest(BaseModel):
    """Schema for document parsing ingestion run statuses."""

    status: str = Field(min_length=1)
    duration_seconds: float | None = None


class MetricsTool(BaseTool):
    """Observability and Prometheus metrics recording tool."""

    def record_chat(self, request: RecordChatRequest) -> None:
        """Record chat message generation trigger."""
        recorders.record_chat_request(mode=request.mode)

    def record_retrieval(self, request: RecordRetrievalRequest) -> None:
        """Record metrics for semantic chunk retrieval."""
        recorders.record_retrieval(
            organization_id=request.organization_id,
            duration_s=request.duration_seconds,
            final_chunks=request.final_chunks,
            avg_similarity=request.avg_similarity,
            rerank_input=request.rerank_input,
            post_dedup=request.post_dedup,
            near_dup_dropped=request.near_dup_dropped,
            top_k=request.top_k,
        )

    def record_generation(self, request: RecordGenerationUsageRequest) -> None:
        """Record LLM token usage details."""
        recorders.record_generation_usage(
            organization_id=request.organization_id,
            provider=request.provider,
            route_type=request.route_type,
            usage=request.usage,
        )

    def record_evaluation(self, request: RecordEvaluationRunRequest) -> None:
        """Record evaluation run completion status counters."""
        recorders.record_evaluation_run(
            run_type=request.run_type,
            status=request.status,
        )

    def record_ingestion(self, request: RecordIngestionJobRequest) -> None:
        """Record document ingestion pipeline run duration."""
        recorders.record_ingestion_job(
            status=request.status,
            duration_s=request.duration_seconds,
        )

    def record_chat_stream_duration(self, duration_seconds: float) -> None:
        """Record total duration of a chat stream response."""
        recorders.record_chat_stream_duration(duration_seconds)

    def record_hallucination(self) -> None:
        """Record hallucination check flag."""
        recorders.record_hallucination_flag()
