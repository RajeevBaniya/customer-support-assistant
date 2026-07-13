"""Observability models representing stages and metrics."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class StageTelemetry(BaseModel):
    """Telemetry data collected for a single pipeline execution stage."""

    model_config = {"frozen": True}

    stage_name: str
    start_time: datetime
    end_time: datetime | None = None
    duration_ms: float | None = None
    status: str = "pending"  # pending, success, failed
    metadata: dict[str, Any] = Field(default_factory=dict)
