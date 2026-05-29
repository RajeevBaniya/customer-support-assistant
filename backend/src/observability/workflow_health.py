from __future__ import annotations

from typing import Any, TypedDict


class WorkflowHealthBundle(TypedDict, total=False):
    workflow_engine_ready: bool
    graph_registry_ready: bool
    workflow_engine_error: str
    graph_registry_error: str


class _WorkflowProbeState(TypedDict, total=False):
    n: int


def _workflow_probe_noop(_state: _WorkflowProbeState) -> dict[str, Any]:
    return {}


def _compile_workflow_probe_graph() -> None:
    from langgraph.graph import END, StateGraph

    graph = StateGraph(_WorkflowProbeState)
    graph.add_node("noop", _workflow_probe_noop)
    graph.set_entry_point("noop")
    graph.add_edge("noop", END)
    graph.compile()


def workflow_health_bundle() -> WorkflowHealthBundle:
    out: WorkflowHealthBundle = {
        "workflow_engine_ready": False,
        "graph_registry_ready": False,
    }
    try:
        _compile_workflow_probe_graph()
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
