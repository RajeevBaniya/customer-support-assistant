from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig

from src.ai.citationBuilder import citations_from_chunks
from src.ai.contextBuilder import build_context_text
from src.ai.promptBuilder import build_prompt_pair
from src.ai.providerRouter import complete_with_fallback
from src.core.appEnvironment import AppEnvironment
from src.retrieval.retrievalService import RetrievalService
from src.schemas.retrievalSchemas import (
    RetrievalChunkItem,
    RetrievalSearchRequest,
    RetrievalSearchResponse,
)
from src.workflows.pipeline import chat_rag_orchestration as orch
from src.workflows.state.chat_rag_state import ChatRagState, scratch_list, trace_event


def _cfg(config: RunnableConfig) -> dict[str, Any]:
    raw = config.get("configurable") or {}
    if not isinstance(raw, dict):
        raise TypeError("configurable must be a dict")
    return raw


def _settings(config: RunnableConfig) -> AppEnvironment:
    s = _cfg(config).get("settings")
    if not isinstance(s, AppEnvironment):
        raise TypeError("settings must be AppEnvironment")
    return s


def _retrieval(config: RunnableConfig) -> RetrievalService:
    r = _cfg(config).get("retrieval")
    if not isinstance(r, RetrievalService):
        raise TypeError("retrieval must be RetrievalService")
    return r


async def prepare_query_node(state: ChatRagState, config: RunnableConfig) -> dict[str, Any]:
    del config
    body = RetrievalSearchRequest.model_validate(state["body"])
    prior = state.get("prior_turns_text")
    blended = orch.blended_retrieval_request(body, prior)
    return {
        "retrieval_body": blended.model_dump(mode="json"),
        "workflow_trace": trace_event(
            {
                "stage": "prepare_query",
                "blended_query_len": len(blended.query),
                "top_k_request": body.top_k,
            }
        ),
    }


async def retrieval_node(state: ChatRagState, config: RunnableConfig) -> dict[str, Any]:
    scratch = scratch_list(_cfg(config))
    try:
        org = orch.parse_organization_id(state["organization_id"])
        body = RetrievalSearchRequest.model_validate(state["retrieval_body"])
        resp = await _retrieval(config).search(organization_id=org, body=body)
        return {
            "retrieval_response": resp.model_dump(mode="json"),
            "retrieval_top_k": resp.top_k,
            "workflow_trace": trace_event(
                {
                    "stage": "retrieval",
                    "top_k": resp.top_k,
                    "items": len(resp.items),
                }
            ),
        }
    except Exception as exc:
        scratch.append({"stage": "retrieval", "error": str(exc), "error_type": type(exc).__name__})
        raise


def route_after_retrieval(state: ChatRagState) -> str:
    resp = RetrievalSearchResponse.model_validate(state["retrieval_response"])
    if not resp.items:
        return "insufficient"
    return "context"


async def insufficient_context_node(state: ChatRagState, config: RunnableConfig) -> dict[str, Any]:
    del config
    resp = RetrievalSearchResponse.model_validate(state["retrieval_response"])
    patch = orch.insufficient_prep(top_k=resp.top_k)
    return {
        **patch,
        "workflow_trace": trace_event(
            {"stage": "insufficient_context", "top_k": resp.top_k, "items": 0}
        ),
    }


async def context_node(state: ChatRagState, config: RunnableConfig) -> dict[str, Any]:
    resp = RetrievalSearchResponse.model_validate(state["retrieval_response"])
    settings = _settings(config)
    capped = orch.cap_chunk_items(resp.items, max_chunks=settings.rag_max_chunks)
    ctx = build_context_text(capped, max_chars=settings.rag_max_context_chars)
    return {
        "capped_items": [c.model_dump(mode="json") for c in capped],
        "context_text": ctx.text,
        "context_truncated": ctx.truncated,
        "workflow_trace": trace_event(
            {
                "stage": "context",
                "capped_chunks": len(capped),
                "truncated": ctx.truncated,
            }
        ),
    }


async def citation_node(state: ChatRagState, config: RunnableConfig) -> dict[str, Any]:
    del config
    capped = [RetrievalChunkItem.model_validate(x) for x in state["capped_items"]]
    cites = citations_from_chunks(capped)
    return {
        "citations_json": [c.model_dump(mode="json") for c in cites],
        "workflow_trace": trace_event({"stage": "citation", "citations": len(cites)}),
    }


async def prompt_node(state: ChatRagState, config: RunnableConfig) -> dict[str, Any]:
    del config
    body = RetrievalSearchRequest.model_validate(state["body"])
    system, user = build_prompt_pair(
        user_query=body.query,
        context_text=state["context_text"],
        prior_turns_text=state.get("prior_turns_text"),
    )
    return {
        "use_llm": True,
        "fixed_reply": None,
        "system": system,
        "user": user,
        "workflow_trace": trace_event(
            {
                "stage": "prompt",
                "system_chars": len(system),
                "user_chars": len(user),
            }
        ),
    }


def route_stream_or_generate(state: ChatRagState) -> str:
    return "stop" if state.get("stream_mode") else "generate"


async def generation_node(state: ChatRagState, config: RunnableConfig) -> dict[str, Any]:
    settings = _settings(config)
    scratch = scratch_list(_cfg(config))
    try:
        if not state.get("use_llm"):
            text = str(state.get("fixed_reply") or "")
            return {
                "answer": text,
                "provider": "none",
                "workflow_trace": trace_event({"stage": "generation", "mode": "fixed"}),
            }
        answer, provider = await complete_with_fallback(
            settings,
            system=state["system"],
            user=state["user"],
            organization_id=orch.parse_organization_id(state["organization_id"]),
            route_type="rag",
        )
        return {
            "answer": answer,
            "provider": provider,
            "workflow_trace": trace_event(
                {"stage": "generation", "mode": "llm", "provider": provider}
            ),
        }
    except Exception as exc:
        scratch.append({"stage": "generation", "error": str(exc), "error_type": type(exc).__name__})
        raise
