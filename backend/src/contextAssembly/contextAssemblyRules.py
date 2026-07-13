"""Pure execution rules for assembling context components."""

from src.ai.citationBuilder import citations_from_chunks
from src.ai.contextBuilder import build_context_text
from src.ai.promptBuilder import build_prompt_pair
from src.contextAssembly.contextAssemblyModels import (
    CitationContext,
    ConversationContext,
    ExecutionMetadata,
    RetrievedContext,
    SystemInstructions,
    WorkspaceContext,
)
from src.conversations.priorTurnsFormat import TurnLine, prior_turns_block
from src.core.appEnvironment import AppEnvironment
from src.planning.executionPlan import ExecutionPlan
from src.runtimeContext.runtimeContext import RuntimeContext
from src.schemas.retrievalSchemas import RetrievalChunkItem, RetrievalSearchResponse


class ContextAssemblyRules:
    """Stateless rules calculating token margins and layout text formatting."""

    @staticmethod
    def assemble_history(
        context: RuntimeContext,
        plan: ExecutionPlan,
        settings: AppEnvironment,
    ) -> ConversationContext:
        """Trims prior messages according to history token budget rules."""
        history_messages = []
        if context.conversation and context.conversation.recent_messages:
            recent = context.conversation.recent_messages
            # Exclude the active user query from the prior history turns list
            if (
                recent[-1].role == "user"
                and recent[-1].content.strip() == context.execution.query.strip()
            ):
                history_messages = recent[:-1]
            else:
                history_messages = recent

        history_block = prior_turns_block(
            [TurnLine(m.role, m.content) for m in history_messages],
            max_chars=settings.chat_history_max_chars,
            max_tokens=plan.budget.max_history_tokens,
        )
        return ConversationContext(
            prior_turns_text=history_block.strip() or None,
            message_count=len(history_messages),
        )

    @staticmethod
    def assemble_retrieved(
        search_response: RetrievalSearchResponse,
        plan: ExecutionPlan,
        settings: AppEnvironment,
    ) -> RetrievedContext:
        """Assembles, caps, and compresses retrieved search chunks."""
        if not plan.retrieval.need_retrieval:
            return RetrievedContext(
                context_text="",
                truncated=False,
                capped_items=[],
                chunk_count=0,
            )

        capped = search_response.items[: settings.rag_max_chunks]
        context_res = build_context_text(
            capped,
            max_chars=settings.rag_max_context_chars,
            max_tokens=plan.budget.max_context_tokens,
        )
        return RetrievedContext(
            context_text=context_res.text,
            truncated=context_res.truncated,
            capped_items=capped,
            chunk_count=len(capped),
        )

    @staticmethod
    def assemble_citations(capped_items: list[RetrievalChunkItem]) -> CitationContext:
        """Generates inline citation ranges and returns unique source count."""
        citations = citations_from_chunks(capped_items)
        unique_docs = {item.document_id for item in capped_items if item.document_id}
        return CitationContext(
            citations=citations,
            source_count=len(unique_docs),
        )

    @staticmethod
    def assemble_workspace(
        context: RuntimeContext,
        plan: ExecutionPlan,
    ) -> WorkspaceContext:
        """Resolves target workspace document scope filtering."""
        if plan.retrieval.need_retrieval and plan.retrieval.metadata_filter:
            doc_ids = plan.retrieval.metadata_filter.document_ids or []
        else:
            doc_ids = [doc.id for doc in context.workspace.selected_documents]
        return WorkspaceContext(document_ids=doc_ids)

    @staticmethod
    def assemble_instructions(
        query: str,
        context_text: str,
        prior_turns_text: str | None,
    ) -> SystemInstructions:
        """Formats deterministic system prompts and user queries."""
        system_prompt, user_prompt = build_prompt_pair(
            user_query=query,
            context_text=context_text,
            prior_turns_text=prior_turns_text,
        )
        return SystemInstructions(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

    @staticmethod
    def assemble_metadata(
        context: RuntimeContext,
        plan: ExecutionPlan,
    ) -> ExecutionMetadata:
        """Prepares tracked execution parameters for logging and monitoring."""
        return ExecutionMetadata(
            query=context.execution.query,
            top_k=context.execution.top_k,
            selected_workflow=plan.workflow.selected_workflow,
            retrieval_mode=plan.retrieval.retrieval_mode,
            concurrency=plan.strategy.concurrency,
        )
