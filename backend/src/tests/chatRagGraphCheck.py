from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from src.core.appEnvironment import AppEnvironment
from src.retrieval.retrievalService import RetrievalService
from src.schemas.retrievalSchemas import RetrievalChunkItem, RetrievalSearchResponse
from src.workflows.graph_registry import ainvoke_chat_rag_graph
from src.workflows.state.chat_rag_state import ChatRagState


def _settings_stub() -> AppEnvironment:
    s = MagicMock(spec=AppEnvironment)
    s.rag_max_chunks = 8
    s.rag_max_context_chars = 4000
    s.rag_max_context_tokens = 6000
    s.llm_timeout_seconds = 10.0
    s.active_llm_provider = "gemini"
    return s


@pytest.mark.asyncio
async def test_chat_rag_graph_insufficient_stream_stops() -> None:
    retrieval = MagicMock(spec=RetrievalService)
    retrieval.search = AsyncMock(
        return_value=RetrievalSearchResponse(items=[], query="blended", top_k=5)
    )
    state: ChatRagState = {
        "organization_id": str(UUID("00000000-0000-4000-8000-000000000099")),
        "stream_mode": True,
        "body": {"query": "hello world there", "top_k": 5, "document_ids": None},
        "prior_turns_text": None,
        "workflow_trace": [],
    }
    cfg: dict[str, object] = {
        "configurable": {
            "retrieval": retrieval,
            "settings": _settings_stub(),
            "trace_scratch": [],
        }
    }
    out = await ainvoke_chat_rag_graph(state, cfg)
    assert out.get("use_llm") is False
    assert out.get("retrieval_top_k") == 5
    assert isinstance(out.get("workflow_trace"), list)


@pytest.mark.asyncio
async def test_chat_rag_graph_full_then_generation(monkeypatch: pytest.MonkeyPatch) -> None:
    ts = datetime.now(UTC)
    uid = UUID("00000000-0000-4000-8000-000000000011")
    chunk = RetrievalChunkItem(
        document_id=uid,
        document_name="doc.pdf",
        chunk_index=0,
        source_page=1,
        similarity_score=0.9,
        parser_type="pdf",
        text="Paris is the capital of France for testing.",
        upload_timestamp=ts,
    )
    retrieval = MagicMock(spec=RetrievalService)
    retrieval.search = AsyncMock(
        return_value=RetrievalSearchResponse(items=[chunk], query="blended", top_k=3)
    )

    async def fake_complete(
        _settings: AppEnvironment,
        *,
        system: str,
        user: str,
        organization_id: object = None,
        route_type: str = "rag",
    ) -> tuple[str, str]:
        del _settings, organization_id, route_type
        assert "hello" in user or "Paris" in user or len(system) > 0
        return "ok", "gemini"

    monkeypatch.setattr(
        "src.workflows.nodes.chat_rag_nodes.complete_with_fallback",
        fake_complete,
    )

    state: ChatRagState = {
        "organization_id": str(uid),
        "stream_mode": False,
        "body": {"query": "hello world there", "top_k": 3, "document_ids": None},
        "prior_turns_text": None,
        "workflow_trace": [],
    }
    cfg: dict[str, object] = {
        "configurable": {
            "retrieval": retrieval,
            "settings": _settings_stub(),
            "trace_scratch": [],
        }
    }
    out = await ainvoke_chat_rag_graph(state, cfg)
    assert out.get("answer") == "ok"
    assert out.get("provider") == "gemini"
    assert len(out.get("citations_json") or []) == 1
