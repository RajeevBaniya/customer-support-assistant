from __future__ import annotations

from typing import Any, NamedTuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.contextAssembly.contextPackage import ContextPackage
from src.core.appEnvironment import AppEnvironment
from src.generation.generationResult import GenerationResult
from src.observability.metrics.recorders import record_rag_citations
from src.observability.observabilityEngine import ObservabilityEngine
from src.observability.structuredLogger import get_logger
from src.planning.executionPlan import ExecutionPlan
from src.planning.queryRewriteModels import QueryRewriteResult
from src.response.responseEngine import ResponseEngine
from src.response.responseModels import ResponseRequest
from src.runtimeContext.runtimeContext import RuntimeContext
from src.runtimeTools.retrieveTool import RetrieveTool
from src.schemas.ragSchemas import CitationItem, RagAskResponse
from src.schemas.retrievalSchemas import RetrievalSearchRequest
from src.workflows.graph_registry import ainvoke_chat_rag_graph
from src.workflows.state.chat_rag_state import ChatRagState

logger = get_logger(__name__)


class RagStreamPrepareResult(NamedTuple):
    """RAG streaming execution preparation parameters."""

    top_k: int
    citations: list[CitationItem]
    use_llm: bool
    system: str
    user: str
    fixed_reply: str | None
    context_package: ContextPackage | None = None


class RagService:
    """Orchestrate RAG pipeline execution via LangGraph workflow."""

    def __init__(
        self,
        session: AsyncSession,
        settings: AppEnvironment,
        *,
        is_evaluation: bool = False,
        context: RuntimeContext | None = None,
        plan: ExecutionPlan | None = None,
        query_rewrite: QueryRewriteResult | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._retrieve_tool = RetrieveTool(session, settings)
        self._is_evaluation = is_evaluation
        self._context = context
        self._plan = plan
        self._query_rewrite = query_rewrite

    @classmethod
    def from_request(
        cls,
        session: AsyncSession,
        settings: AppEnvironment,
        *,
        is_evaluation: bool = False,
        context: RuntimeContext | None = None,
        plan: ExecutionPlan | None = None,
        query_rewrite: QueryRewriteResult | None = None,
    ) -> RagService:
        """Factory constructor."""
        return cls(
            session,
            settings,
            is_evaluation=is_evaluation,
            context=context,
            plan=plan,
            query_rewrite=query_rewrite,
        )

    def _graph_config(
        self,
        context: RuntimeContext,
        plan: ExecutionPlan,
        observability: ObservabilityEngine | None = None,
    ) -> dict[str, Any]:
        return {
            "configurable": {
                "retrieve_tool": self._retrieve_tool,
                "settings": self._settings,
                "trace_scratch": [],
                "is_evaluation": self._is_evaluation,
                "context": context,
                "plan": plan,
                "observability": observability,
                "query_rewrite_result": self._query_rewrite,
            }
        }

    async def _ensure_context_and_plan(
        self,
        *,
        organization_id: UUID,
        body: RetrievalSearchRequest,
        prior_turns_text: str | None,
        context: RuntimeContext | None = None,
        plan: ExecutionPlan | None = None,
    ) -> tuple[RuntimeContext, ExecutionPlan]:
        if context is not None and plan is not None:
            return context, plan
        if self._context is not None and self._plan is not None:
            return self._context, self._plan

        from datetime import UTC, datetime
        from uuid import uuid4

        from sqlalchemy import select

        from src.models.userModel import User
        from src.planning.planningEngine import PlanningEngine
        from src.runtimeContext.runtimeContext import ContextMessage, ConversationContext
        from src.runtimeContext.runtimeContextLoader import RuntimeContextLoader

        stmt = select(User).where(User.organization_id == organization_id).limit(1)
        res = await self._session.execute(stmt)
        user = res.scalar_one_or_none()
        if not user:
            raise ValueError(f"No user found for organization {organization_id}")

        loader = RuntimeContextLoader(self._session, self._settings)
        fallback_context = await loader.load(
            user_id=user.id,
            organization_id=organization_id,
            conversation_id=None,
            query=body.query.strip(),
            top_k=body.top_k or self._settings.retrieval_default_top_k,
            document_ids=body.document_ids,
        )

        if prior_turns_text and prior_turns_text.strip():
            messages = []
            for line in prior_turns_text.strip().split("\n"):
                if ":" in line:
                    role_part, content_part = line.split(":", 1)
                    role = role_part.strip().lower()
                    if role in {"user", "assistant"}:
                        messages.append(
                            ContextMessage(
                                id=uuid4(),
                                role=role,
                                content=content_part.strip(),
                                created_at=datetime.now(UTC),
                            )
                        )
            if messages:
                fallback_context.conversation = ConversationContext(
                    conversation_id=uuid4(),
                    title="Ad-hoc Conversation",
                    recent_messages=messages,
                )

        planner = PlanningEngine(self._settings)
        fallback_plan = await planner.plan(fallback_context)
        return fallback_context, fallback_plan

    async def _invoke_chat_rag(
        self,
        *,
        organization_id: UUID,
        search_request: RetrievalSearchRequest,
        prior_turns_text: str | None,
        stream_mode: bool,
        context: RuntimeContext | None = None,
        plan: ExecutionPlan | None = None,
        query_rewrite: QueryRewriteResult | None = None,
        observability: ObservabilityEngine | None = None,
    ) -> ChatRagState:
        if query_rewrite is not None:
            self._query_rewrite = query_rewrite

        state: ChatRagState = {
            "organization_id": str(organization_id),
            "stream_mode": stream_mode,
            "body": search_request.model_dump(mode="json"),
            "prior_turns_text": prior_turns_text,
            "workflow_trace": [],
        }
        if self._query_rewrite is not None:
            state["query_rewrite_result"] = self._query_rewrite
        resolved_context, resolved_plan = await self._ensure_context_and_plan(
            organization_id=organization_id,
            body=search_request,
            prior_turns_text=prior_turns_text,
            context=context,
            plan=plan,
        )
        config = self._graph_config(resolved_context, resolved_plan, observability)
        try:
            return await ainvoke_chat_rag_graph(state, config)
        except Exception:
            trace_scratch = config.get("configurable", {}).get("trace_scratch")
            if isinstance(trace_scratch, list) and trace_scratch:
                logger.warning("chat_rag_graph_failed", trace_scratch=trace_scratch)
            raise

    async def prepare_stream_prompt(
        self,
        *,
        organization_id: UUID,
        body: RetrievalSearchRequest,
        prior_turns_text: str | None,
        context: RuntimeContext | None = None,
        plan: ExecutionPlan | None = None,
        query_rewrite: QueryRewriteResult | None = None,
        observability: ObservabilityEngine | None = None,
    ) -> RagStreamPrepareResult:
        """Prepare inputs for a streaming RAG query."""
        state = await self._invoke_chat_rag(
            organization_id=organization_id,
            search_request=body,
            prior_turns_text=prior_turns_text,
            stream_mode=True,
            context=context,
            plan=plan,
            query_rewrite=query_rewrite,
            observability=observability,
        )
        citations_raw = state.get("citations_json") or []
        citations = [CitationItem.model_validate(citation) for citation in citations_raw]
        top_k = int(state.get("retrieval_top_k") or 0)
        package_raw = state.get("context_package")
        package = ContextPackage.model_validate(package_raw) if package_raw else None

        return RagStreamPrepareResult(
            top_k=top_k,
            citations=citations,
            use_llm=bool(state.get("use_llm")),
            system=str(state.get("system") or ""),
            user=str(state.get("user") or ""),
            fixed_reply=state.get("fixed_reply"),
            context_package=package,
        )

    async def ask_with_graph_state(
        self,
        *,
        organization_id: UUID,
        body: RetrievalSearchRequest,
        prior_turns_text: str | None = None,
        context: RuntimeContext | None = None,
        plan: ExecutionPlan | None = None,
        query_rewrite: QueryRewriteResult | None = None,
        observability: ObservabilityEngine | None = None,
    ) -> tuple[RagAskResponse, ChatRagState]:
        """Execute complete RAG workflow and return LangGraph state."""
        state = await self._invoke_chat_rag(
            organization_id=organization_id,
            search_request=body,
            prior_turns_text=prior_turns_text,
            stream_mode=False,
            context=context,
            plan=plan,
            query_rewrite=query_rewrite,
            observability=observability,
        )
        top_k = int(state.get("retrieval_top_k") or 0)
        gen_raw = state.get("generation_result")
        pkg_raw = state.get("context_package")

        if gen_raw and pkg_raw:
            gen_res = GenerationResult.model_validate(gen_raw)
            pkg = ContextPackage.model_validate(pkg_raw)
            request = ResponseRequest(
                generation_result=gen_res,
                context_package=pkg,
            )
            engine = ResponseEngine(self._settings)
            res = engine.compile(request)
            response = RagAskResponse(
                answer=res.assistant_text,
                citations=res.citations,
                provider=res.provider_used,
                retrieval_top_k=top_k,
            )
            record_rag_citations(len(res.citations))
        else:
            citations_raw = state.get("citations_json") or []
            citations = [CitationItem.model_validate(citation) for citation in citations_raw]
            response = RagAskResponse(
                answer=str(state.get("answer") or state.get("fixed_reply") or ""),
                citations=citations,
                provider="none",
                retrieval_top_k=top_k,
            )
            record_rag_citations(len(citations))

        return response, state

    async def ask(
        self,
        *,
        organization_id: UUID,
        body: RetrievalSearchRequest,
        prior_turns_text: str | None = None,
        context: RuntimeContext | None = None,
        plan: ExecutionPlan | None = None,
        observability: ObservabilityEngine | None = None,
    ) -> RagAskResponse:
        """Execute complete RAG workflow and return response payload."""
        response, _state = await self.ask_with_graph_state(
            organization_id=organization_id,
            body=body,
            prior_turns_text=prior_turns_text,
            context=context,
            plan=plan,
            observability=observability,
        )
        return response
