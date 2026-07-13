"""Workflow coordination for evaluation runs."""

from typing import Any
from uuid import UUID

from src.ai.ragService import RagService
from src.core.appEnvironment import AppEnvironment
from src.evaluation.pipelines.evaluation_graph_runner import run_evaluation_graph_pass
from src.runtimeTools.retrieveTool import RetrieveTool
from src.schemas.retrievalSchemas import RetrievalSearchRequest


async def run_evaluation_flow(
    *,
    settings: AppEnvironment,
    organization_id: UUID,
    query: str,
    reference_answer: str | None,
    retrieve_tool: RetrieveTool,
) -> dict[str, Any]:
    """Execute evaluation graph pass by instantiating RAG service with tool session."""
    session = retrieve_tool._session
    rag = RagService(session, settings, is_evaluation=True)
    body = RetrievalSearchRequest(
        query=query,
        top_k=settings.retrieval_default_top_k,
    )
    return await run_evaluation_graph_pass(
        rag=rag,
        organization_id=organization_id,
        body=body,
        prior_turns_text=None,
    )
