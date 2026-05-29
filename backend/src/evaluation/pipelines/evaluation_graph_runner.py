from __future__ import annotations

from time import perf_counter
from typing import Any, cast
from uuid import UUID

from src.ai.ragService import RagService
from src.evaluation.pipelines.evaluation_graph_registry import get_compiled_evaluation_graph
from src.observability.metrics.recorders import record_workflow_graph
from src.observability.tracing.correlation import start_workflow_trace
from src.schemas.retrievalSchemas import RetrievalSearchRequest


async def run_evaluation_graph_pass(
    *,
    rag: RagService,
    organization_id: UUID,
    body: RetrievalSearchRequest,
    prior_turns_text: str | None,
) -> dict[str, Any]:
    start_workflow_trace()
    graph = get_compiled_evaluation_graph()
    state: dict[str, Any] = {
        "organization_id": str(organization_id),
        "body": body.model_dump(mode="json"),
        "prior_turns_text": prior_turns_text,
    }
    cfg: dict[str, Any] = {"configurable": {"rag": rag}}
    t0 = perf_counter()
    status = "ok"
    try:
        return cast(dict[str, Any], await graph.ainvoke(state, cfg))
    except Exception:
        status = "error"
        raise
    finally:
        record_workflow_graph(graph="evaluation", status=status, duration_s=perf_counter() - t0)
