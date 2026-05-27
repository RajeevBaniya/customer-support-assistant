from __future__ import annotations

from typing import Any, TypedDict, cast
from uuid import UUID

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph

from src.ai.ragService import RagService
from src.evaluation.scoring.evaluationScoreBundle import compute_evaluation_scores
from src.evaluation.scoring.textSignals import chunk_refs_from_state, summarize_workflow_trace
from src.schemas.ragSchemas import CitationItem, RagAskResponse
from src.schemas.retrievalSchemas import RetrievalSearchRequest
from src.workflows.state.chat_rag_state import ChatRagState


class EvaluationGraphState(TypedDict, total=False):
    organization_id: str
    body: dict[str, Any]
    prior_turns_text: str | None
    rag_response: dict[str, Any]
    graph_pack: dict[str, Any]
    workflow_trace_summary: dict[str, Any] | None
    scores: dict[str, float]


def _cfg(config: RunnableConfig) -> dict[str, Any]:
    raw = config.get("configurable") or {}
    if not isinstance(raw, dict):
        raise TypeError("configurable must be a dict")
    return raw


def _pack_graph(st: ChatRagState) -> dict[str, Any]:
    return {
        "context_text": str(st.get("context_text") or ""),
        "capped_items": st.get("capped_items") or [],
        "workflow_trace": st.get("workflow_trace") or [],
        "retrieval_top_k": int(st.get("retrieval_top_k") or 0),
    }


async def evaluation_execute_node(
    state: EvaluationGraphState,
    config: RunnableConfig,
) -> dict[str, Any]:
    rag = _cfg(config).get("rag")
    if not isinstance(rag, RagService):
        raise TypeError("rag must be RagService")
    org = UUID(state["organization_id"])
    body = RetrievalSearchRequest.model_validate(state["body"])
    prior = state.get("prior_turns_text")
    response, graph_state = await rag.ask_with_graph_state(
        organization_id=org,
        body=body,
        prior_turns_text=prior,
    )
    return {
        "rag_response": response.model_dump(mode="json"),
        "graph_pack": _pack_graph(graph_state),
        "workflow_trace_summary": summarize_workflow_trace(graph_state),
    }


def evaluation_score_node(state: EvaluationGraphState, config: RunnableConfig) -> dict[str, Any]:
    del config
    resp = RagAskResponse.model_validate(state["rag_response"])
    pack = state["graph_pack"]
    context = str(pack.get("context_text") or "")[:32000]
    refs = chunk_refs_from_state(cast(ChatRagState, {"capped_items": pack.get("capped_items")}))
    body = RetrievalSearchRequest.model_validate(state["body"])
    citations = [CitationItem.model_validate(x) for x in resp.citations]
    scores = compute_evaluation_scores(
        query=body.query,
        answer=resp.answer,
        context=context,
        chunk_refs=refs,
        citations_count=len(citations),
        top_k=resp.retrieval_top_k,
    )
    return {"scores": scores}


def build_evaluation_graph() -> StateGraph:
    g = StateGraph(EvaluationGraphState)
    g.add_node("execute", evaluation_execute_node)
    g.add_node("score", evaluation_score_node)
    g.set_entry_point("execute")
    g.add_edge("execute", "score")
    g.add_edge("score", END)
    return g
