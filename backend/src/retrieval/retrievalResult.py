"""RetrievalResult model containing normalized search chunks and metrics."""

from typing import Any

from pydantic import BaseModel

from src.retrieval.retrievalMetrics import RetrievalMetrics
from src.schemas.ragSchemas import CitationItem
from src.schemas.retrievalSchemas import RetrievalChunkItem


class RetrievalResult(BaseModel):
    """Immutable result structure enclosing normalized search chunks and citations."""

    model_config = {"frozen": True}

    retrieved_chunks: list[RetrievalChunkItem]
    scores: list[float]
    citations: list[CitationItem]
    metadata: dict[str, Any]
    retrieval_metrics: RetrievalMetrics
    provider_metadata: dict[str, Any] | None = None
