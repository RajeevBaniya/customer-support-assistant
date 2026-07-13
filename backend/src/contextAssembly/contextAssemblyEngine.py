"""ContextAssemblyEngine coordinating assembly rules to build immutable ContextPackages."""

from time import perf_counter

from src.contextAssembly.contextAssemblyRules import ContextAssemblyRules
from src.contextAssembly.contextPackage import ContextPackage
from src.core.appEnvironment import AppEnvironment
from src.observability.structuredLogger import get_logger
from src.planning.executionPlan import ExecutionPlan
from src.runtimeContext.runtimeContext import RuntimeContext
from src.schemas.retrievalSchemas import RetrievalSearchResponse

logger = get_logger("context_assembly.engine")


class ContextAssemblyEngine:
    """Pure context assembly compiler coordinating prompt templates and token margins."""

    def __init__(self, settings: AppEnvironment) -> None:
        self._settings = settings

    def assemble(
        self,
        context: RuntimeContext,
        plan: ExecutionPlan,
        search_response: RetrievalSearchResponse,
    ) -> ContextPackage:
        """Assembles a ContextPackage by executing modular rules."""
        start_time = perf_counter()

        conversation = ContextAssemblyRules.assemble_history(
            context, plan, self._settings
        )
        retrieved = ContextAssemblyRules.assemble_retrieved(
            search_response, plan, self._settings
        )
        citations = ContextAssemblyRules.assemble_citations(retrieved.capped_items)
        workspace = ContextAssemblyRules.assemble_workspace(context, plan)
        instructions = ContextAssemblyRules.assemble_instructions(
            query=context.execution.query,
            context_text=retrieved.context_text,
            prior_turns_text=conversation.prior_turns_text,
        )
        metadata = ContextAssemblyRules.assemble_metadata(context, plan)

        package = ContextPackage(
            conversation=conversation,
            retrieved=retrieved,
            workspace=workspace,
            metadata=metadata,
            instructions=instructions,
            citations=citations,
        )

        duration = perf_counter() - start_time
        logger.info(
            "context_assembly_completed",
            assembly_duration_seconds=duration,
            retrieved_chunk_count=retrieved.chunk_count,
            history_message_count=conversation.message_count,
            final_context_size_chars=len(retrieved.context_text),
            source_count=citations.source_count,
        )
        return package
