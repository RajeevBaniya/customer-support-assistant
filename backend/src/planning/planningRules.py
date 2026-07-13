"""Pure rule definitions evaluating RuntimeContext parameters for Planning decisions."""

import re

from src.core.appEnvironment import AppEnvironment
from src.planning.planningModels import (
    ExecutionStrategy,
    MetadataFilter,
    RetrievalDecision,
    TokenBudget,
    WorkflowDecision,
)
from src.runtimeContext.runtimeContext import RuntimeContext

_COMPARE_KEYWORDS = re.compile(
    r"\b(compare|comparison|vs|versus|difference)\b",
    re.IGNORECASE,
)


class PlanningRules:
    """Isolated, stateless rules determining routing and bounds for execution."""

    @staticmethod
    def determine_workflow(context: RuntimeContext) -> WorkflowDecision:
        """Determines execution workflow based on comparison intent keywords."""
        query = context.execution.query.strip()
        if _COMPARE_KEYWORDS.search(query):
            return WorkflowDecision(
                selected_workflow="ComparisonWorkflow",
                reason="Query contains comparison terms",
            )
        return WorkflowDecision(
            selected_workflow="DefaultChatWorkflow",
            reason="Default chat flow",
        )

    @staticmethod
    def determine_retrieval(context: RuntimeContext) -> RetrievalDecision:
        """Determines semantic retrieval necessity and scopes metadata parameters."""
        doc_ids = context.execution.document_ids
        if doc_ids and len(doc_ids) > 0:
            mode = "hybrid" if context.execution.hybrid_retrieval_enabled else "semantic"
            meta = MetadataFilter(
                organization_id=context.session.organization_id,
                document_ids=doc_ids,
            )
            return RetrievalDecision(
                need_retrieval=True,
                retrieval_mode=mode,
                metadata_filter=meta,
            )
        return RetrievalDecision(
            need_retrieval=False,
            retrieval_mode="none",
            metadata_filter=None,
        )

    @staticmethod
    def determine_budget(context: RuntimeContext, settings: AppEnvironment) -> TokenBudget:
        """Calculates token memory budget based on environment configurations."""
        del context
        return TokenBudget(
            max_context_tokens=settings.rag_max_context_tokens,
            max_history_tokens=settings.chat_memory_max_tokens,
        )

    @staticmethod
    def determine_strategy(workflow: WorkflowDecision) -> ExecutionStrategy:
        """Determines processing strategy based on workflow type."""
        if workflow.selected_workflow == "ComparisonWorkflow":
            return ExecutionStrategy(concurrency="concurrent")
        return ExecutionStrategy(concurrency="sequential")
