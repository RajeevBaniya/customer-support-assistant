"""WorkflowMetrics model representing execution performance stats."""

from pydantic import BaseModel


class WorkflowMetrics(BaseModel):
    """Immutable model encapsulating RAG pipeline execution step durations."""

    model_config = {"frozen": True}

    total_duration_ms: float
    context_load_duration_ms: float
    planning_duration_ms: float
    execution_duration_ms: float
    stages_executed: list[str]
    stages_skipped: list[str]
