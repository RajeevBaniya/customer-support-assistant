from __future__ import annotations

from uuid import UUID

from src.ai.citationBuilder import citations_from_chunks
from src.ai.contextBuilder import build_context_text
from src.ai.promptBuilder import build_prompt_pair, load_insufficient_context_answer
from src.core.appEnvironment import AppEnvironment
from src.schemas.ragSchemas import CitationItem
from src.schemas.retrievalSchemas import RetrievalChunkItem, RetrievalSearchRequest

BLENDED_RETRIEVAL_QUERY_MAX = 800


def blend_retrieval_query(*, latest: str, prior_turns: str | None) -> str:
    text = latest.strip()
    if prior_turns is None or not prior_turns.strip():
        return text[:BLENDED_RETRIEVAL_QUERY_MAX]
    prior = prior_turns.strip()
    cap = BLENDED_RETRIEVAL_QUERY_MAX
    if len(text) >= cap:
        return text[:cap]
    sep = "\n\n"
    room = cap - len(text) - len(sep)
    if room <= 0:
        return text[:cap]
    tail = prior[-room:] if len(prior) > room else prior
    return f"{text}{sep}{tail}"[:cap]


def blended_retrieval_request(
    body: RetrievalSearchRequest,
    prior_turns_text: str | None,
) -> RetrievalSearchRequest:
    blended = blend_retrieval_query(latest=body.query, prior_turns=prior_turns_text)
    return body.model_copy(update={"query": blended})


def cap_chunk_items(
    items: list[RetrievalChunkItem],
    *,
    max_chunks: int,
) -> list[RetrievalChunkItem]:
    return items[:max_chunks]


def insufficient_prep(
    *,
    top_k: int,
) -> dict[str, object]:
    return {
        "use_llm": False,
        "fixed_reply": load_insufficient_context_answer(),
        "citations_json": [],
        "system": "",
        "user": "",
        "retrieval_top_k": top_k,
    }


def build_context_and_prompts(
    *,
    capped: list[RetrievalChunkItem],
    user_query: str,
    prior_turns_text: str | None,
    settings: AppEnvironment,
) -> tuple[str, str, list[CitationItem], int, str, bool]:
    ctx = build_context_text(capped, max_chars=settings.rag_max_context_chars)
    system, user = build_prompt_pair(
        user_query=user_query,
        context_text=ctx.text,
        prior_turns_text=prior_turns_text,
    )
    cites = citations_from_chunks(capped)
    return system, user, cites, len(capped), ctx.text, ctx.truncated


def parse_organization_id(value: str) -> UUID:
    return UUID(value)
