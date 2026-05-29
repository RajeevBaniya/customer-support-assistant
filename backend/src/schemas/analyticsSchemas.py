from src.schemas.commonSchemas import ApiModel


class TokenAnalyticsSummary(ApiModel):
    hours: int
    totals: dict[str, int]
    by_provider: dict[str, dict[str, int]]
    by_route: dict[str, dict[str, int]]
    estimated_event_count: int


class RetrievalAnalyticsSummary(ApiModel):
    hours: int
    sample_count: int
    avg_chunks: float
    avg_similarity: float
    avg_rerank_reduction_pct: float
    total_near_dup_dropped: int
    avg_sufficiency: float


class EvaluationAnalyticsSummary(ApiModel):
    hours: int
    result_count: int
    pass_count: int
    fail_count: int
    avg_faithfulness: float
    avg_hallucination: float
    avg_retrieval_relevance: float


class IngestionAnalyticsSummary(ApiModel):
    hours: int
    job_count: int
    status_counts: dict[str, int]
    avg_duration_seconds: float
