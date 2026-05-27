from __future__ import annotations

from typing import Any, cast

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
    app = get_compiled_chat_rag_graph()
    out = cast(ChatRagState, await app.ainvoke(state, config))
    scratch = config.get("configurable", {}).get("trace_scratch")
    if isinstance(scratch, list) and scratch:
        return merge_failure_trace(out, scratch)
    return out
