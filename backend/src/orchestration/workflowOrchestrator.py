"""WorkflowOrchestrator driving unified planning, retrieval, assembly, and generation execution."""

from collections.abc import AsyncIterator
from time import perf_counter

from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.citationBuilder import citations_from_chunks
from src.ai.ragService import RagService
from src.contextAssembly.contextPackage import ContextPackage
from src.core.appEnvironment import AppEnvironment
from src.generation.generationEngine import GenerationEngine
from src.generation.generationModels import GenerationRequest
from src.generation.generationResult import GenerationResult
from src.observability.observabilityEngine import ObservabilityEngine
from src.observability.structuredLogger import get_logger
from src.orchestration.workflowMetrics import WorkflowMetrics
from src.orchestration.workflowRequest import WorkflowRequest
from src.orchestration.workflowResult import WorkflowResult
from src.planning.planningEngine import PlanningEngine
from src.response.responseEngine import ResponseEngine
from src.response.responseModels import ResponseRequest
from src.response.responseResult import ResponseResult
from src.retrieval.retrievalMetrics import RetrievalMetrics
from src.retrieval.retrievalResult import RetrievalResult
from src.runtimeContext.runtimeContextLoader import RuntimeContextLoader
from src.schemas.retrievalSchemas import RetrievalSearchRequest, RetrievalSearchResponse

logger = get_logger("workflow.orchestrator")


class WorkflowOrchestrator:
    """Orchestration boundary coordinating loaders, planners, and generation engines."""

    def __init__(self, session: AsyncSession, settings: AppEnvironment) -> None:
        self._session = session
        self._settings = settings
        self._observability = ObservabilityEngine(session, settings)

    async def execute(
        self, request: WorkflowRequest, prior_turns_text: str | None = None
    ) -> WorkflowResult:
        """Executes the synchronous pipeline and returns the compiled WorkflowResult."""
        total_start = perf_counter()
        self._observability.start_trace(workflow_id="rag_chat")

        # 1. Load context
        self._observability.start_stage("context_loader")
        loader_start = perf_counter()
        loader = RuntimeContextLoader(self._session, self._settings)
        context = await loader.load(
            user_id=request.user_id,
            organization_id=request.organization_id,
            conversation_id=request.conversation_id,
            query=request.user_message.strip(),
            top_k=self._settings.retrieval_default_top_k,
            document_ids=request.selected_document_ids,
        )
        loader_ms = (perf_counter() - loader_start) * 1000.0
        self._observability.end_stage("context_loader", status="success")

        # 2. Planning
        self._observability.start_stage("planner")
        plan_start = perf_counter()
        planner = PlanningEngine(self._settings)
        plan = planner.plan(context)
        plan_ms = (perf_counter() - plan_start) * 1000.0

        if prior_turns_text is None:
            from src.conversations.priorTurnsFormat import TurnLine, prior_turns_block

            recent = context.conversation.recent_messages if context.conversation else []
            prior_messages = recent[:-1]
            history_block = prior_turns_block(
                [TurnLine(m.role, m.content) for m in prior_messages],
                max_chars=self._settings.chat_history_max_chars,
                max_tokens=plan.budget.max_history_tokens,
            )
            prior_turns_text = history_block.strip() or None
        self._observability.end_stage("planner", status="success")

        # 3. Execution (via RagService and LangGraph state)
        self._observability.start_stage("rag_graph")
        exec_start = perf_counter()
        rag_service = RagService.from_request(
            self._session,
            self._settings,
            context=context,
            plan=plan,
            is_evaluation=request.evaluation_mode,
        )
        search_req = RetrievalSearchRequest(
            query=request.user_message.strip(),
            top_k=context.execution.top_k,
            document_ids=request.selected_document_ids,
        )
        ask_response, state = await rag_service.ask_with_graph_state(
            organization_id=request.organization_id,
            body=search_req,
            prior_turns_text=prior_turns_text,
            context=context,
            plan=plan,
            observability=self._observability,
        )
        exec_ms = (perf_counter() - exec_start) * 1000.0
        self._observability.end_stage("rag_graph", status="success")

        # 4. Extract stage payloads
        gen_raw = state.get("generation_result")
        pkg_raw = state.get("context_package")
        ret_raw = state.get("retrieval_response")

        generation_result = None
        if gen_raw:
            generation_result = GenerationResult.model_validate(gen_raw)

        context_package = None
        if pkg_raw:
            context_package = ContextPackage.model_validate(pkg_raw)

        retrieval_result = None
        if ret_raw:
            search_resp = RetrievalSearchResponse.model_validate(ret_raw)
            retrieval_result = RetrievalResult(
                retrieved_chunks=search_resp.items,
                scores=[item.similarity_score for item in search_resp.items],
                citations=citations_from_chunks(search_resp.items),
                metadata={"query": search_resp.query},
                retrieval_metrics=RetrievalMetrics(
                    retrieval_latency_ms=0.0,
                    returned_chunk_count=len(search_resp.items),
                    filtered_chunk_count=0,
                    top_k_used=search_resp.top_k,
                    retrieval_mode=plan.retrieval.retrieval_mode,
                ),
            )

        # 5. Compile final ResponseResult
        if generation_result and context_package:
            response_engine = ResponseEngine(self._settings, observability=self._observability)
            response_result = response_engine.compile(
                ResponseRequest(
                    generation_result=generation_result,
                    context_package=context_package,
                )
            )
        else:
            # Fallback early exit response compilation
            response_engine = ResponseEngine(self._settings, observability=self._observability)
            mock_gen = GenerationResult(
                assistant_text=ask_response.answer,
                finish_reason="stop",
                provider_used="none",
                model_used="none",
                latency_ms=0.0,
                fallback_used=False,
            )
            mock_pkg = ContextPackage(
                conversation=state.get("prior_turns_text"),  # type: ignore
                retrieved=state.get("retrieval_response"),  # type: ignore
                workspace=state.get("body"),  # type: ignore
                metadata=state.get("body"),  # type: ignore
                instructions=state.get("body"),  # type: ignore
                citations=state.get("body"),  # type: ignore
            )
            response_result = response_engine.compile(
                ResponseRequest(
                    generation_result=mock_gen,
                    context_package=mock_pkg,
                )
            )

        total_ms = (perf_counter() - total_start) * 1000.0
        self._observability.finish_trace(status="success")

        metrics = WorkflowMetrics(
            total_duration_ms=total_ms,
            context_load_duration_ms=loader_ms,
            planning_duration_ms=plan_ms,
            execution_duration_ms=exec_ms,
            stages_executed=["context_loader", "planner", "rag_graph"],
            stages_skipped=[],
        )

        return WorkflowResult(
            response_result=response_result,
            execution_plan=plan,
            runtime_context=context,
            generation_result=generation_result,
            retrieval_result=retrieval_result,
            context_package=context_package,
            execution_metadata={
                "provider_used": response_result.provider_used,
                "fallback_used": response_result.fallback_used,
            },
            workflow_metrics=metrics,
        )

    async def stream_execute(
        self, request: WorkflowRequest, prior_turns_text: str | None = None
    ) -> AsyncIterator[ResponseResult]:
        """Orchestrates streaming RAG generation yielding incremental ResponseResult objects."""
        self._observability.start_trace(workflow_id="rag_chat_stream")

        # 1. Load context & plan
        self._observability.start_stage("context_loader")
        loader = RuntimeContextLoader(self._session, self._settings)
        context = await loader.load(
            user_id=request.user_id,
            organization_id=request.organization_id,
            conversation_id=request.conversation_id,
            query=request.user_message.strip(),
            top_k=self._settings.retrieval_default_top_k,
            document_ids=request.selected_document_ids,
        )
        self._observability.end_stage("context_loader", status="success")

        self._observability.start_stage("planner")
        planner = PlanningEngine(self._settings)
        plan = planner.plan(context)

        if prior_turns_text is None:
            from src.conversations.priorTurnsFormat import TurnLine, prior_turns_block

            recent = context.conversation.recent_messages if context.conversation else []
            prior_messages = recent[:-1]
            history_block = prior_turns_block(
                [TurnLine(m.role, m.content) for m in prior_messages],
                max_chars=self._settings.chat_history_max_chars,
                max_tokens=plan.budget.max_history_tokens,
            )
            prior_turns_text = history_block.strip() or None
        self._observability.end_stage("planner", status="success")

        # 2. Run graph preparation
        self._observability.start_stage("rag_graph")
        rag_service = RagService.from_request(
            self._session,
            self._settings,
            context=context,
            plan=plan,
            is_evaluation=request.evaluation_mode,
        )
        search_req = RetrievalSearchRequest(
            query=request.user_message.strip(),
            top_k=context.execution.top_k,
            document_ids=request.selected_document_ids,
        )
        prep = await rag_service.prepare_stream_prompt(
            organization_id=request.organization_id,
            body=search_req,
            prior_turns_text=prior_turns_text,
            context=context,
            plan=plan,
            observability=self._observability,
        )
        self._observability.end_stage("rag_graph", status="success")

        # 3. Check early exits
        if not prep.use_llm:
            response_engine = ResponseEngine(self._settings, observability=self._observability)
            mock_gen = GenerationResult(
                assistant_text=prep.fixed_reply or "",
                finish_reason="stop",
                provider_used="none",
                model_used="none",
                latency_ms=0.0,
                fallback_used=False,
            )
            mock_pkg = ContextPackage(
                conversation=prep.citations,  # type: ignore
                retrieved=prep.citations,  # type: ignore
                workspace=prep.citations,  # type: ignore
                metadata=prep.citations,  # type: ignore
                instructions=prep.citations,  # type: ignore
                citations=prep.citations,  # type: ignore
            )
            yield response_engine.compile(
                ResponseRequest(generation_result=mock_gen, context_package=mock_pkg)
            )
            self._observability.finish_trace(status="success")
            return

        # 4. Stream generate using compiled ContextPackage
        package = prep.context_package
        if not package:
            # Fallback empty construction
            from src.contextAssembly.contextAssemblyEngine import ContextAssemblyEngine

            assembly = ContextAssemblyEngine(self._settings)
            search_resp = RetrievalSearchResponse(
                query=request.user_message.strip(),
                top_k=request.selected_document_ids and len(request.selected_document_ids) or 0,
                items=[],
            )
            package = assembly.assemble(context, plan, search_resp)

        gen_req = GenerationRequest(
            context_package=package,
            organization_id=request.organization_id,
            stream=True,
            is_evaluation=request.evaluation_mode,
        )

        generation_engine = GenerationEngine(self._settings, observability=self._observability)
        response_engine = ResponseEngine(self._settings, observability=self._observability)

        async for chunk in generation_engine.stream_generate(gen_req):
            chunk_req = ResponseRequest(
                generation_result=chunk,
                context_package=package,
            )
            yield response_engine.compile(chunk_req)

        self._observability.finish_trace(status="success")
