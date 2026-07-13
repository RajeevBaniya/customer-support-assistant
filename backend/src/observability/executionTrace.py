"""ExecutionTrace model wrapping overall pipeline execution telemetry."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.observability.observabilityModels import StageTelemetry


class ExecutionTrace(BaseModel):
    """Immutable trace summarizing overall latency and outcomes of all executed stages."""

    model_config = {"frozen": True}

    execution_id: UUID
    workflow_id: str
    request_id: str | None = None
    start_time: datetime
    end_time: datetime | None = None
    total_latency_ms: float | None = None
    executed_stages: list[str] = Field(default_factory=list)
    skipped_stages: list[str] = Field(default_factory=list)
    provider_used: str | None = None
    fallback_used: bool = False
    status: str = "success"  # success, failed
    stages: list[StageTelemetry] = Field(default_factory=list)
