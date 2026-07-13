from __future__ import annotations

import json
import re
from typing import Any

from src.schemas.evaluationSchemas import (
    MAX_RETRIEVED_CONTEXT_CHARS,
    MAX_WORKFLOW_TRACE_SUMMARY_CHARS,
)
from src.shared.textHelpers import split_sentences
from src.workflows.state.chat_rag_state import ChatRagState

_TOKEN = re.compile(r"[a-z0-9]{2,}")


def token_set(text: str) -> set[str]:
    return set(_TOKEN.findall(text.lower()))


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / max(1, union)


def sentence_chunks(text: str) -> list[str]:
    return split_sentences(text)


def best_sentence_overlap(sentence: str, context: str) -> float:
    if not sentence.strip():
        return 1.0
    s_tok = token_set(sentence)
    if not s_tok:
        return 1.0
    best = 0.0
    for ctx_sentence in sentence_chunks(context):
        best = max(best, jaccard(s_tok, token_set(ctx_sentence)))
    best = max(best, jaccard(s_tok, token_set(context)))
    return best


def truncate_context_text(raw: str) -> str:
    if len(raw) <= MAX_RETRIEVED_CONTEXT_CHARS:
        return raw
    return raw[: MAX_RETRIEVED_CONTEXT_CHARS - 3] + "..."


def chunk_refs_from_state(state: ChatRagState) -> list[dict[str, Any]]:
    capped = state.get("capped_items") or []
    out: list[dict[str, Any]] = []
    for row in capped:
        if not isinstance(row, dict):
            continue
        out.append(
            {
                "document_id": row.get("document_id"),
                "chunk_index": row.get("chunk_index"),
                "document_name": row.get("document_name"),
                "similarity_score": row.get("similarity_score"),
            }
        )
    return out


def build_retrieved_context(state: ChatRagState) -> str:
    return truncate_context_text(str(state.get("context_text") or ""))


def summarize_workflow_trace(state: ChatRagState) -> dict[str, Any] | None:
    trace = state.get("workflow_trace")
    if not isinstance(trace, list) or not trace:
        return None
    payload: dict[str, Any] = {"stages": trace[-32:], "total": len(trace)}
    text = json.dumps(payload, default=str, separators=(",", ":"))
    if len(text) <= MAX_WORKFLOW_TRACE_SUMMARY_CHARS:
        return payload
    return {
        "truncated": True,
        "total": len(trace),
        "tail": trace[-8:],
    }
