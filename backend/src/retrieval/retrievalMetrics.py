"""RetrievalMetrics model representing execution performance stats."""

from pydantic import BaseModel


class RetrievalMetrics(BaseModel):
    """Immutable model representing latency and count stats for retrieval queries."""

    model_config = {"frozen": True}

    retrieval_latency_ms: float
    returned_chunk_count: int
    filtered_chunk_count: int
    top_k_used: int
    retrieval_mode: str
