"""ResponseMetrics model representing performance bounds."""

from pydantic import BaseModel


class ResponseMetrics(BaseModel):
    """Immutable model representing compilation latencies and citation count stats."""

    model_config = {"frozen": True}

    response_latency_ms: float
    response_size_chars: int
    citation_count: int
    provider: str
    fallback: bool
