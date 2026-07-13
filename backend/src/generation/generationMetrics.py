"""GenerationMetrics model representing execution stats."""

from pydantic import BaseModel


class GenerationMetrics(BaseModel):
    """Immutable model encapsulating generation tokens and latency counts."""

    model_config = {"frozen": True}

    request_duration: float
    provider_latency: float
    completion_tokens: int
    prompt_tokens: int
    retry_count: int
