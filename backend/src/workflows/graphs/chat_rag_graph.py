from __future__ import annotations

from langgraph.graph import END, StateGraph

from src.workflows.nodes.chat_rag_nodes import (
    citation_node,
    context_node,
    generation_node,
    insufficient_context_node,
    prepare_query_node,
    prompt_node,
    retrieval_node,
    route_after_retrieval,
    route_stream_or_generate,
)
from src.workflows.state.chat_rag_state import ChatRagState


def build_chat_rag_graph() -> StateGraph:
    g = StateGraph(ChatRagState)
    g.add_node("prepare_query", prepare_query_node)
    g.add_node("retrieval", retrieval_node)
    g.add_node("insufficient", insufficient_context_node)
    g.add_node("context", context_node)
    g.add_node("citation", citation_node)
    g.add_node("prompt", prompt_node)
    g.add_node("generation", generation_node)
    g.set_entry_point("prepare_query")
    g.add_edge("prepare_query", "retrieval")
    g.add_conditional_edges(
        "retrieval",
        route_after_retrieval,
        {"insufficient": "insufficient", "context": "context"},
    )
    g.add_edge("context", "citation")
    g.add_edge("citation", "prompt")
    g.add_conditional_edges(
        "prompt",
        route_stream_or_generate,
        {"stop": END, "generate": "generation"},
    )
    g.add_conditional_edges(
        "insufficient",
        route_stream_or_generate,
        {"stop": END, "generate": "generation"},
    )
    g.add_edge("generation", END)
    return g
