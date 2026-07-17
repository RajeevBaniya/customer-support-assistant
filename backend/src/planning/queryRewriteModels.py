"""QueryRewriteResult model packaging query intelligence metadata."""

from typing import Any

from pydantic import BaseModel, Field


class QueryRewriteResult(BaseModel):
    """Immutable results payload returned by the QueryRewriteAgent."""

    model_config = {"frozen": True}

    original_query: str
    rewritten_query: str
    rewrite_performed: bool
    rewrite_reason: str
    detected_entities: list[str] = Field(default_factory=list)
    detected_acronyms: list[str] = Field(default_factory=list)
    expanded_terms: list[str] = Field(default_factory=list)
    retrieval_queries: list[str] = Field(default_factory=list)
    confidence: float
    metadata: dict[str, Any] = Field(default_factory=dict)
