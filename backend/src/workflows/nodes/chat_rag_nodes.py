from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig

from src.contextAssembly.contextAssemblyEngine import ContextAssemblyEngine
from src.contextAssembly.contextPackage import ContextPackage
from src.core.appEnvironment import AppEnvironment
from src.generation.generationEngine import GenerationEngine
from src.generation.generationModels import GenerationRequest
from src.planning.executionPlan import ExecutionPlan
from src.retrieval.retrievalEngine import RetrievalEngine
from src.retrieval.retrievalModels import RetrievalRequest
from src.runtimeContext.runtimeContext import RuntimeContext
from src.runtimeTools.retrieveTool import RetrieveTool
from src.schemas.retrievalSchemas import (
    RetrievalSearchRequest,
    RetrievalSearchResponse,
)
from src.workflows.pipeline import chat_rag_orchestration as orchestration
from src.workflows.state.chat_rag_state import ChatRagState, scratch_list, trace_event


def get_configurable(config: RunnableConfig) -> dict[str, Any]:
    """Retrieve configurable parameters dictionary from execution context."""
    configurable = config.get("configurable") or {}
    if not isinstance(configurable, dict):
        raise TypeError("configurable must be a dict")
    return configurable


def get_app_settings(config: RunnableConfig) -> AppEnvironment:
    """Retrieve AppEnvironment settings from execution context."""
    settings = get_configurable(config).get("settings")
    if not isinstance(settings, AppEnvironment):
        raise TypeError("settings must be AppEnvironment")
    return settings


def get_execution_plan(config: RunnableConfig) -> ExecutionPlan:
    """Retrieve ExecutionPlan from execution context."""
    plan = get_configurable(config).get("plan")
    if not isinstance(plan, ExecutionPlan):
        raise TypeError("plan must be ExecutionPlan")
    return plan


def get_runtime_context(config: RunnableConfig) -> RuntimeContext:
    """Retrieve RuntimeContext from execution context."""
    context = get_configurable(config).get("context")
    if not isinstance(context, RuntimeContext):
        raise TypeError("context must be RuntimeContext")
    return context


def get_retrieval_tool(config: RunnableConfig) -> RetrieveTool:
    """Retrieve RetrieveTool instance from execution context."""
    retrieval_tool = get_configurable(config).get("retrieve_tool")
    if not isinstance(retrieval_tool, RetrieveTool):
        raise TypeError("retrieve_tool must be RetrieveTool")
    return retrieval_tool


async def prepare_query_node(state: ChatRagState, config: RunnableConfig) -> dict[str, Any]:
    """Prepare search query using history context or intelligent rewritten query."""
    config_val = get_configurable(config).get("query_rewrite_result")
    query_rewrite = state.get("query_rewrite_result") or config_val
    search_request = RetrievalSearchRequest.model_validate(state["body"])

    if query_rewrite and query_rewrite.rewrite_performed:
        blended_request = search_request.model_copy(
            update={"query": query_rewrite.rewritten_query}
        )
        rewrite_performed = True
    else:
        prior_turns_text = state.get("prior_turns_text")
        blended_request = orchestration.blended_retrieval_request(search_request, prior_turns_text)
        rewrite_performed = False

    res: dict[str, Any] = {
        "retrieval_body": blended_request.model_dump(mode="json"),
        "workflow_trace": trace_event(
            {
                "stage": "prepare_query",
                "blended_query_len": len(blended_request.query),
                "top_k_request": search_request.top_k,
                "rewrite_performed": rewrite_performed,
            }
        ),
    }
    if query_rewrite:
        res["query_rewrite_result"] = query_rewrite
    return res


async def retrieval_node(state: ChatRagState, config: RunnableConfig) -> dict[str, Any]:
    """Run semantic document chunk search using RetrievalEngine."""
    trace_scratch = scratch_list(get_configurable(config))
    settings = get_app_settings(config)
    plan = get_execution_plan(config)
    context = get_runtime_context(config)
    search_request = RetrievalSearchRequest.model_validate(state["retrieval_body"])

    try:
        tool = get_retrieval_tool(config)
        observability = get_configurable(config).get("observability")
        engine = RetrievalEngine(tool, settings, observability=observability)
        org_id = orchestration.parse_organization_id(state["organization_id"])

        request = RetrievalRequest(
            execution_plan=plan,
            runtime_context=context,
            organization_id=org_id,
            query=search_request.query,
            top_k=search_request.top_k,
            retrieval_mode=plan.retrieval.retrieval_mode,
        )

        result = await engine.retrieve(request)

        search_response = RetrievalSearchResponse(
            items=result.retrieved_chunks,
            query=request.query,
            top_k=result.retrieval_metrics.top_k_used,
        )

        return {
            "retrieval_response": search_response.model_dump(mode="json"),
            "retrieval_top_k": search_response.top_k,
            "workflow_trace": trace_event(
                {
                    "stage": "retrieval",
                    "top_k": search_response.top_k,
                    "items": len(search_response.items),
                }
            ),
        }
    except Exception as exception:
        trace_scratch.append({
            "stage": "retrieval",
            "error": str(exception),
            "error_type": type(exception).__name__,
        })
        raise


def route_after_retrieval(state: ChatRagState) -> str:
    """Route node flow based on whether any search hits were returned."""
    search_response = RetrievalSearchResponse.model_validate(state["retrieval_response"])
    if not search_response.items:
        return "insufficient"
    return "context"


async def insufficient_context_node(state: ChatRagState, config: RunnableConfig) -> dict[str, Any]:
    """Prepare fallback properties when search returned no results."""
    del config
    search_response = RetrievalSearchResponse.model_validate(state["retrieval_response"])
    patch = orchestration.insufficient_prep(top_k=search_response.top_k)
    return {
        **patch,
        "workflow_trace": trace_event(
            {"stage": "insufficient_context", "top_k": search_response.top_k, "items": 0}
        ),
    }


async def context_node(state: ChatRagState, config: RunnableConfig) -> dict[str, Any]:
    """Run context assembly compiler to build pristine immutable ContextPackage."""
    search_response = RetrievalSearchResponse.model_validate(state["retrieval_response"])
    settings = get_app_settings(config)
    plan = get_execution_plan(config)
    context = get_runtime_context(config)

    assembly = ContextAssemblyEngine(settings)
    package = assembly.assemble(context, plan, search_response)

    return {
        "context_package": package.model_dump(mode="json"),
        "capped_items": [item.model_dump(mode="json") for item in package.retrieved.capped_items],
        "context_text": package.retrieved.context_text,
        "context_truncated": package.retrieved.truncated,
        "workflow_trace": trace_event(
            {
                "stage": "context",
                "capped_chunks": package.retrieved.chunk_count,
                "truncated": package.retrieved.truncated,
            }
        ),
    }


async def citation_node(state: ChatRagState, config: RunnableConfig) -> dict[str, Any]:
    """Retrieve citation metadata from assembled ContextPackage."""
    del config
    package_raw = state.get("context_package")
    if package_raw:
        package = ContextPackage.model_validate(package_raw)
        citations = package.citations.citations
    else:
        citations = []
    return {
        "citations_json": [citation.model_dump(mode="json") for citation in citations],
        "workflow_trace": trace_event({"stage": "citation", "citations": len(citations)}),
    }


async def prompt_node(state: ChatRagState, config: RunnableConfig) -> dict[str, Any]:
    """Construct final system and user instructions using assembled ContextPackage."""
    del config
    package_raw = state.get("context_package")
    if not package_raw:
        return {
            "use_llm": True,
            "fixed_reply": None,
            "system": "",
            "user": state.get("body", {}).get("query", ""),
        }
    package = ContextPackage.model_validate(package_raw)
    system_prompt = package.instructions.system_prompt
    user_prompt = package.instructions.user_prompt
    return {
        "use_llm": True,
        "fixed_reply": None,
        "system": system_prompt,
        "user": user_prompt,
        "workflow_trace": trace_event(
            {
                "stage": "prompt",
                "system_chars": len(system_prompt),
                "user_chars": len(user_prompt),
            }
        ),
    }


def route_stream_or_generate(state: ChatRagState) -> str:
    """Route flow node based on streaming preference choice."""
    return "stop" if state.get("stream_mode") else "generate"


async def generation_node(state: ChatRagState, config: RunnableConfig) -> dict[str, Any]:
    """Execute LLM text generation or emit fixed reply fallback."""
    settings = get_app_settings(config)
    trace_scratch = scratch_list(get_configurable(config))
    try:
        if not state.get("use_llm"):
            reply_text = str(state.get("fixed_reply") or "")
            return {
                "answer": reply_text,
                "provider": "none",
                "workflow_trace": trace_event({"stage": "generation", "mode": "fixed"}),
            }
        is_evaluation = bool(get_configurable(config).get("is_evaluation", False))
        package_raw = state["context_package"]
        package = ContextPackage.model_validate(package_raw)

        request = GenerationRequest(
            context_package=package,
            organization_id=orchestration.parse_organization_id(state["organization_id"]),
            stream=False,
            is_evaluation=is_evaluation,
        )

        observability = get_configurable(config).get("observability")
        engine = GenerationEngine(settings, observability=observability)
        result = await engine.generate(request)

        return {
            "answer": result.assistant_text,
            "provider": result.provider_used,
            "generation_result": result.model_dump(mode="json"),
            "workflow_trace": trace_event(
                {"stage": "generation", "mode": "llm", "provider": result.provider_used}
            ),
        }
    except Exception as exception:
        trace_scratch.append({
            "stage": "generation",
            "error": str(exception),
            "error_type": type(exception).__name__,
        })
        raise
