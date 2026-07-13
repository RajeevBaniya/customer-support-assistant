"""ResponseResult model containing compilation outputs and execution metadata."""

from typing import Any

from pydantic import BaseModel

from src.response.responseMetrics import ResponseMetrics
from src.schemas.ragSchemas import CitationItem


class ResponseResult(BaseModel):
    """Immutable final assistant response model consumed by downstream callers."""

    model_config = {"frozen": True}

    assistant_text: str
    citations: list[CitationItem]
    provider_used: str
    model_used: str
    finish_reason: str | None = None
    fallback_used: bool
    usage: dict[str, int] | None = None
    execution_metadata: dict[str, Any]
    response_metrics: ResponseMetrics
