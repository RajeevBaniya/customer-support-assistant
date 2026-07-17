from __future__ import annotations

from prometheus_client import Counter, Histogram

HTTP_REQUESTS = Counter(
    "recallstack_http_requests_total",
    "Total HTTP requests",
    ["method", "route", "status_code"],
)

HTTP_LATENCY = Histogram(
    "recallstack_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "route"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)

CHAT_REQUESTS = Counter(
    "recallstack_chat_requests_total",
    "Chat message requests",
    ["mode"],
)

CHAT_STREAM_DURATION = Histogram(
    "recallstack_chat_stream_duration_seconds",
    "Chat SSE stream duration",
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
)

RETRIEVAL_REQUESTS = Counter(
    "recallstack_retrieval_requests_total",
    "Retrieval search requests",
)

RETRIEVAL_LATENCY = Histogram(
    "recallstack_retrieval_duration_seconds",
    "Retrieval search latency",
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

RETRIEVAL_CHUNKS = Histogram(
    "recallstack_retrieval_chunks",
    "Retrieved chunk count per search",
    buckets=(0, 1, 2, 3, 5, 8, 12, 20, 50),
)

RETRIEVAL_CITATIONS = Histogram(
    "recallstack_rag_citations",
    "Citation count per RAG answer",
    buckets=(0, 1, 2, 3, 5, 8, 12, 20),
)

EVALUATION_RUNS = Counter(
    "recallstack_evaluation_runs_total",
    "Evaluation runs started",
    ["run_type", "status"],
)

EVALUATION_HALLUCINATION_FLAGS = Counter(
    "recallstack_evaluation_hallucination_flags_total",
    "Evaluation results flagged as high hallucination risk",
)

INGESTION_JOBS = Counter(
    "recallstack_ingestion_jobs_total",
    "Ingestion jobs observed via API lifecycle",
    ["status"],
)

INGESTION_DURATION = Histogram(
    "recallstack_ingestion_duration_seconds",
    "Ingestion job duration when completed via API",
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0),
)

GENERATION_TOKENS = Counter(
    "recallstack_generation_tokens_total",
    "LLM tokens consumed",
    ["provider", "route_type", "token_kind", "estimated"],
)

WORKFLOW_GRAPH_RUNS = Counter(
    "recallstack_workflow_graph_runs_total",
    "LangGraph workflow executions",
    ["graph", "status"],
)

WORKFLOW_GRAPH_DURATION = Histogram(
    "recallstack_workflow_graph_duration_seconds",
    "LangGraph workflow duration",
    ["graph"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

WORKFLOW_NODE_RUNS = Counter(
    "recallstack_workflow_node_runs_total",
    "LangGraph node executions",
    ["graph", "node", "status"],
)

HYBRID_RETRIEVAL_REQUESTS = Counter(
    "recallstack_hybrid_retrieval_requests_total",
    "Total hybrid retrieval requests",
)

HYBRID_CANDIDATE_POOL_SIZE = Histogram(
    "recallstack_hybrid_candidate_pool_size",
    "Hybrid retrieval candidate pool size",
    buckets=(10, 20, 50, 75, 100, 150, 200, 300),
)

HYBRID_RRF_DURATION = Histogram(
    "recallstack_hybrid_rrf_duration_seconds",
    "Hybrid RRF merge duration",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)


INGESTION_PARSING_LATENCY = Histogram(
    "recallstack_ingestion_parsing_duration_seconds",
    "Ingestion parsing latency",
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

INGESTION_CHUNKING_LATENCY = Histogram(
    "recallstack_ingestion_chunking_duration_seconds",
    "Ingestion semantic chunking latency",
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

INGESTION_EMBEDDING_LATENCY = Histogram(
    "recallstack_ingestion_embedding_duration_seconds",
    "Ingestion embedding latency",
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

INGESTION_INDEXING_LATENCY = Histogram(
    "recallstack_ingestion_indexing_duration_seconds",
    "Ingestion indexing latency",
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

INGESTION_CHUNKS_GENERATED = Histogram(
    "recallstack_ingestion_chunks_generated",
    "Total chunks generated per document during ingestion",
    buckets=(1, 5, 10, 20, 50, 100, 250, 500, 1000),
)

INGESTION_DUPLICATES_REMOVED = Histogram(
    "recallstack_ingestion_duplicates_removed",
    "Duplicate chunks removed per document during ingestion",
    buckets=(0, 1, 5, 10, 20, 50, 100, 250, 500),
)

INGESTION_CHUNK_SIZE_AVG = Histogram(
    "recallstack_ingestion_chunk_size_average_chars",
    "Average chunk size in characters per document during ingestion",
    buckets=(100, 250, 500, 750, 1000, 1250, 1500, 2000),
)

INGESTION_BATCH_COUNT = Histogram(
    "recallstack_ingestion_batch_count",
    "Total embedding batches executed per document during ingestion",
    buckets=(1, 2, 5, 10, 20, 50, 100),
)


