from __future__ import annotations

from time import perf_counter
from uuid import UUID

from src.ai.generationUsage import GenerationUsage
from src.observability.metrics import registry as m
from src.observability.metrics.org_window_store import append_org_event


def record_http_request(*, method: str, route: str, status_code: int, duration_s: float) -> None:
    m.HTTP_REQUESTS.labels(method=method, route=route, status_code=str(status_code)).inc()
    m.HTTP_LATENCY.labels(method=method, route=route).observe(duration_s)


def record_chat_request(*, mode: str) -> None:
    m.CHAT_REQUESTS.labels(mode=mode).inc()


def record_chat_stream_duration(duration_s: float) -> None:
    m.CHAT_STREAM_DURATION.observe(duration_s)


def record_retrieval(
    *,
    organization_id: UUID | None,
    duration_s: float,
    final_chunks: int,
    avg_similarity: float,
    rerank_input: int,
    post_dedup: int,
    near_dup_dropped: int,
    top_k: int,
) -> None:
    m.RETRIEVAL_REQUESTS.inc()
    m.RETRIEVAL_LATENCY.observe(duration_s)
    m.RETRIEVAL_CHUNKS.observe(float(final_chunks))
    if organization_id is not None:
        rerank_reduction = 0.0
        if rerank_input > 0:
            rerank_reduction = max(0.0, (rerank_input - post_dedup) / rerank_input)
        sufficiency = min(1.0, final_chunks / max(1, top_k))
        append_org_event(
            organization_id=organization_id,
            kind="retrieval",
            payload={
                "final_chunks": final_chunks,
                "avg_similarity": avg_similarity,
                "rerank_reduction_pct": round(rerank_reduction * 100.0, 2),
                "near_dup_dropped": near_dup_dropped,
                "sufficiency": round(sufficiency, 4),
                "duration_ms": int(duration_s * 1000.0),
            },
        )


def record_rag_citations(count: int) -> None:
    m.RETRIEVAL_CITATIONS.observe(float(count))


def record_evaluation_run(*, run_type: str, status: str) -> None:
    m.EVALUATION_RUNS.labels(run_type=run_type, status=status).inc()


def record_hallucination_flag() -> None:
    m.EVALUATION_HALLUCINATION_FLAGS.inc()


def record_ingestion_job(*, status: str, duration_s: float | None = None) -> None:
    m.INGESTION_JOBS.labels(status=status).inc()
    if duration_s is not None:
        m.INGESTION_DURATION.observe(duration_s)


def record_generation_usage(
    *,
    organization_id: UUID | None,
    provider: str,
    route_type: str,
    usage: GenerationUsage,
) -> None:
    est = "true" if usage.estimated else "false"
    m.GENERATION_TOKENS.labels(
        provider=provider,
        route_type=route_type,
        token_kind="prompt",
        estimated=est,
    ).inc(usage.prompt_tokens)
    m.GENERATION_TOKENS.labels(
        provider=provider,
        route_type=route_type,
        token_kind="completion",
        estimated=est,
    ).inc(usage.completion_tokens)
    m.GENERATION_TOKENS.labels(
        provider=provider,
        route_type=route_type,
        token_kind="total",
        estimated=est,
    ).inc(usage.total_tokens)
    if organization_id is not None:
        append_org_event(
            organization_id=organization_id,
            kind="token",
            payload={
                "provider": provider,
                "route_type": route_type,
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
                "estimated": usage.estimated,
            },
        )


def record_workflow_graph(*, graph: str, status: str, duration_s: float) -> None:
    m.WORKFLOW_GRAPH_RUNS.labels(graph=graph, status=status).inc()
    m.WORKFLOW_GRAPH_DURATION.labels(graph=graph).observe(duration_s)


def record_workflow_node(*, graph: str, node: str, status: str) -> None:
    m.WORKFLOW_NODE_RUNS.labels(graph=graph, node=node, status=status).inc()


class observe_workflow_node:
    def __init__(self, *, graph: str, node: str) -> None:
        self._graph = graph
        self._node = node
        self._t0 = 0.0

    def __enter__(self) -> observe_workflow_node:
        self._t0 = perf_counter()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        status = "error" if exc_type is not None else "ok"
        record_workflow_node(graph=self._graph, node=self._node, status=status)
        del self._t0
