"""GenerationResult model containing final generation outputs and execution metadata."""

from pydantic import BaseModel


class GenerationResult(BaseModel):
    """Immutable result structure enclosing LLM assistant output text and providers markers."""

    model_config = {"frozen": True}

    assistant_text: str
    finish_reason: str | None = None
    provider_used: str
    model_used: str
    token_usage: dict[str, int] | None = None
    latency_ms: float
    fallback_used: bool
