from __future__ import annotations

from typing import Any, TypedDict


class WorkflowHealthBundle(TypedDict, total=False):
    workflow_engine_ready: bool
    graph_registry_ready: bool
    workflow_engine_error: str
    graph_registry_error: str


def workflow_health_bundle() -> WorkflowHealthBundle:
    out: WorkflowHealthBundle = {
        "workflow_engine_ready": False,
        "graph_registry_ready": False,
    }
    try:
        from langgraph.graph import END, StateGraph

        class _ProbeState(TypedDict, total=False):
            n: int

        def _noop(s: _ProbeState) -> dict[str, Any]:
            return {}

        g = StateGraph(_ProbeState)
        g.add_node("noop", _noop)
        g.set_entry_point("noop")
        g.add_edge("noop", END)
        g.compile()
        out["workflow_engine_ready"] = True
    except Exception as exc:
        out["workflow_engine_error"] = str(exc)

    try:
        from src.workflows.graph_registry import register_chat_rag_graph

        register_chat_rag_graph()
        out["graph_registry_ready"] = True
    except Exception as exc:
        out["graph_registry_error"] = str(exc)

    return out
