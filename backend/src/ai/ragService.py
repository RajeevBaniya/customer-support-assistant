from __future__ import annotations

from typing import Any, NamedTuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.appEnvironment import AppEnvironment
from src.observability.structuredLogger import get_logger
from src.retrieval.retrievalService import RetrievalService
from src.schemas.ragSchemas import CitationItem, RagAskResponse
from src.schemas.retrievalSchemas import RetrievalSearchRequest
from src.workflows.graph_registry import ainvoke_chat_rag_graph
from src.workflows.state.chat_rag_state import ChatRagState

logger = get_logger(__name__)


class RagStreamPrepareResult(NamedTuple):
    top_k: int
    citations: list[CitationItem]
    use_llm: bool
    system: str
    user: str
    fixed_reply: str | None


class RagService:
    def __init__(self, session: AsyncSession, settings: AppEnvironment) -> None:
        self._settings = settings
        self._retrieval = RetrievalService.from_request(session, settings)

    @classmethod
    def from_request(cls, session: AsyncSession, settings: AppEnvironment) -> RagService:
        return cls(session, settings)

    def _graph_config(self) -> dict[str, Any]:
        return {
            "configurable": {
                "retrieval": self._retrieval,
                "settings": self._settings,
                "trace_scratch": [],
            }
        }

    async def _invoke_chat_rag(
        self,
        *,
        organization_id: UUID,
        body: RetrievalSearchRequest,
        prior_turns_text: str | None,
        stream_mode: bool,
    ) -> ChatRagState:
        state: ChatRagState = {
            "organization_id": str(organization_id),
            "stream_mode": stream_mode,
            "body": body.model_dump(mode="json"),
            "prior_turns_text": prior_turns_text,
            "workflow_trace": [],
        }
        cfg = self._graph_config()
        try:
            return await ainvoke_chat_rag_graph(state, cfg)
        except Exception:
            scratch = cfg.get("configurable", {}).get("trace_scratch")
            if isinstance(scratch, list) and scratch:
                logger.warning("chat_rag_graph_failed", trace_scratch=scratch)
            raise

    async def prepare_stream_prompt(
        self,
        *,
        organization_id: UUID,
        body: RetrievalSearchRequest,
        prior_turns_text: str | None,
    ) -> RagStreamPrepareResult:
        st = await self._invoke_chat_rag(
            organization_id=organization_id,
            body=body,
            prior_turns_text=prior_turns_text,
            stream_mode=True,
        )
        cites_raw = st.get("citations_json") or []
        citations = [CitationItem.model_validate(x) for x in cites_raw]
        top_k = int(st.get("retrieval_top_k") or 0)
        return RagStreamPrepareResult(
            top_k=top_k,
            citations=citations,
            use_llm=bool(st.get("use_llm")),
            system=str(st.get("system") or ""),
            user=str(st.get("user") or ""),
            fixed_reply=st.get("fixed_reply"),
        )

    async def ask_with_graph_state(
        self,
        *,
        organization_id: UUID,
        body: RetrievalSearchRequest,
        prior_turns_text: str | None = None,
    ) -> tuple[RagAskResponse, ChatRagState]:
        st = await self._invoke_chat_rag(
            organization_id=organization_id,
            body=body,
            prior_turns_text=prior_turns_text,
            stream_mode=False,
        )
        cites_raw = st.get("citations_json") or []
        citations = [CitationItem.model_validate(x) for x in cites_raw]
        top_k = int(st.get("retrieval_top_k") or 0)
        response = RagAskResponse(
            answer=str(st.get("answer") or ""),
            citations=citations,
            provider=str(st.get("provider") or "none"),
            retrieval_top_k=top_k,
        )
        return response, st

    async def ask(
        self,
        *,
        organization_id: UUID,
        body: RetrievalSearchRequest,
        prior_turns_text: str | None = None,
    ) -> RagAskResponse:
        response, _st = await self.ask_with_graph_state(
            organization_id=organization_id,
            body=body,
            prior_turns_text=prior_turns_text,
        )
        return response
