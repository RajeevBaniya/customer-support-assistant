from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from typing import Annotated, Any, TypedDict

from src.observability.tracing.workflow_trace import enrich_trace_row
from src.workflows.trace.workflow_trace_reducer import workflow_trace_reducer


class ChatRagState(TypedDict, total=False):
    organization_id: str
    stream_mode: bool
    body: dict[str, Any]
    prior_turns_text: str | None
    workflow_trace: Annotated[list[dict[str, Any]], workflow_trace_reducer]
    retrieval_body: dict[str, Any]
    retrieval_response: dict[str, Any]
    capped_items: list[dict[str, Any]]
    context_text: str
    context_truncated: bool
    citations_json: list[dict[str, Any]]
    system: str
    user: str
    use_llm: bool
    fixed_reply: str | None
    retrieval_top_k: int
    answer: str
    provider: str
    context_package: dict[str, Any]
    generation_result: dict[str, Any]


def trace_event(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    stage = str(row.get("stage") or "unknown")
    enriched = enrich_trace_row(row, graph="chat_rag", node=stage)
    return [enriched]


def scratch_list(configurable: MutableMapping[str, Any]) -> list[dict[str, Any]]:
    raw = configurable.setdefault("trace_scratch", [])
    if not isinstance(raw, list):
        raise TypeError("trace_scratch must be a list")
    return raw
