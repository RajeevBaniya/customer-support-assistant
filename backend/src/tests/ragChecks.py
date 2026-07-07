from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from httpx import AsyncClient

from src.ai.citationBuilder import citations_from_chunks
from src.ai.contextBuilder import build_context_text
from src.ai.promptBuilder import build_prompt_pair, load_insufficient_context_answer
from src.ai.providerRouter import complete_with_fallback
from src.core.appEnvironment import AppEnvironment
from src.schemas.retrievalSchemas import RetrievalChunkItem
from src.workflows.pipeline.chat_rag_orchestration import (
    BLENDED_RETRIEVAL_QUERY_MAX,
    blend_retrieval_query,
)


def test_build_context_text_truncates() -> None:
    long_text = "x" * 5000
    item = RetrievalChunkItem(
        document_id=UUID("00000000-0000-4000-8000-000000000001"),
        document_name="a.pdf",
        chunk_index=0,
        source_page=1,
        similarity_score=0.9,
        parser_type="pdf",
        text=long_text,
        upload_timestamp=datetime.now(UTC),
    )
    out = build_context_text([item], max_chars=200)
    assert len(out.text) <= 200
    assert out.text.endswith("...")
    assert out.truncated is True


def test_context_text_removes_duplicate_sentences() -> None:
    ts = datetime.now(UTC)
    uid = UUID("00000000-0000-4000-8000-000000000002")
    body = "First long sentence here. Second unique sentence here. First long sentence here."
    item = RetrievalChunkItem(
        document_id=uid,
        document_name="b.pdf",
        chunk_index=0,
        source_page=1,
        similarity_score=0.8,
        parser_type="pdf",
        text=body,
        upload_timestamp=ts,
    )
    out = build_context_text([item], max_chars=5000)
    assert out.duplicate_sentences_removed >= 1
    assert "Second unique" in out.text


def test_blend_retrieval_query_respects_cap() -> None:
    prior = "p" * 2000
    out = blend_retrieval_query(latest="hello world", prior_turns=prior)
    assert len(out) <= BLENDED_RETRIEVAL_QUERY_MAX
    assert out.startswith("hello world")


def test_citations_dedupe_same_chunk_twice() -> None:
    ts = datetime.now(UTC)
    uid = UUID("00000000-0000-4000-8000-000000000001")
    a = RetrievalChunkItem(
        document_id=uid,
        document_name="a.pdf",
        chunk_index=0,
        source_page=1,
        similarity_score=0.5,
        parser_type="pdf",
        text="t",
        upload_timestamp=ts,
    )
    b = RetrievalChunkItem(
        document_id=uid,
        document_name="a.pdf",
        chunk_index=0,
        source_page=1,
        similarity_score=0.5,
        parser_type="pdf",
        text="t",
        upload_timestamp=ts,
    )
    cites = citations_from_chunks([a, b])
    assert len(cites) == 1


def test_citations_from_chunks_shape() -> None:
    ts = datetime.now(UTC)
    items = [
        RetrievalChunkItem(
            document_id=UUID("00000000-0000-4000-8000-000000000001"),
            document_name="a.pdf",
            chunk_index=0,
            source_page=2,
            similarity_score=0.5,
            parser_type="pdf",
            text="hi",
            upload_timestamp=ts,
        )
    ]
    cites = citations_from_chunks(items)
    assert len(cites) == 1
    assert cites[0].chunk_index == 0
    assert cites[0].source_page == 2


def test_build_prompt_pair_renders_query_and_context() -> None:
    system, user = build_prompt_pair(user_query="why?", context_text="ctx")
    assert "why?" in user
    assert "ctx" in user
    assert len(system) > 10


def test_load_insufficient_context_non_empty() -> None:
    assert len(load_insufficient_context_answer()) > 20


@pytest.mark.asyncio
async def test_provider_fallback_order(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    async def boom(
        _settings: AppEnvironment,
        *,
        system: str,
        user: str,
        timeout_seconds: float,
    ) -> tuple[str, None]:
        del system, user, timeout_seconds
        calls.append("groq")
        raise RuntimeError("groq_down")

    async def ok(
        _settings: AppEnvironment,
        *,
        system: str,
        user: str,
        timeout_seconds: float,
    ) -> tuple[str, None]:
        del system, user, timeout_seconds
        calls.append("gemini")
        return "answer", None

    monkeypatch.setattr("src.ai.providerRouter.groq_chat", boom)
    monkeypatch.setattr("src.ai.providerRouter.gemini_chat", ok)

    settings = MagicMock(spec=AppEnvironment)
    settings.active_llm_provider = "groq"
    settings.llm_timeout_seconds = 10.0
    settings.groq_api_key = "k"
    settings.gemini_api_key = "g"

    text, used = await complete_with_fallback(settings, system="s", user="u")
    assert text == "answer"
    assert used == "gemini"
    assert calls == ["groq", "gemini"]


@pytest.mark.asyncio
async def test_rag_ask_requires_auth(async_client: AsyncClient) -> None:
    response = await async_client.post(
        "/api/v1/rag/ask",
        json={"query": "hello world"},
    )
    assert response.status_code == 401
