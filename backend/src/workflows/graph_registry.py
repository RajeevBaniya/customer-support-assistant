from __future__ import annotations

from time import perf_counter
from typing import Any, cast

from src.observability.metrics.recorders import record_workflow_graph, record_workflow_node
from src.observability.tracing.correlation import start_workflow_trace
from src.workflows.graphs.chat_rag_graph import build_chat_rag_graph
from src.workflows.state.chat_rag_state import ChatRagState
from src.workflows.trace.workflow_trace_reducer import workflow_trace_reducer

_compiled: Any = None


def get_compiled_chat_rag_graph() -> Any:
    global _compiled
    if _compiled is None:
        _compiled = build_chat_rag_graph().compile()
    return _compiled


def register_chat_rag_graph() -> Any:
    return get_compiled_chat_rag_graph()


def merge_failure_trace(state: ChatRagState, scratch: list[dict[str, Any]]) -> ChatRagState:
    if not scratch:
        return state
    merged = workflow_trace_reducer(state.get("workflow_trace"), scratch)
    out = dict(state)
    out["workflow_trace"] = merged
    return cast(ChatRagState, out)


async def ainvoke_chat_rag_graph(
    state: ChatRagState,
    config: dict[str, Any],
) -> ChatRagState:
    start_workflow_trace()
    app = get_compiled_chat_rag_graph()
    t0 = perf_counter()
    status = "ok"
    try:
        out = cast(ChatRagState, await app.ainvoke(state, config))
    except Exception:
        status = "error"
        scratch = config.get("configurable", {}).get("trace_scratch")
        if isinstance(scratch, list):
            for row in scratch:
                if isinstance(row, dict):
                    stage = str(row.get("stage") or "unknown")
                    record_workflow_node(graph="chat_rag", node=stage, status="error")
        raise
    finally:
        record_workflow_graph(graph="chat_rag", status=status, duration_s=perf_counter() - t0)
    scratch = config.get("configurable", {}).get("trace_scratch")
    if isinstance(scratch, list) and scratch:
        return merge_failure_trace(out, scratch)
    return out
