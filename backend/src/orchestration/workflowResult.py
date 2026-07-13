"""WorkflowResult model encapsulating planning, contexts, and compile outputs."""

from typing import Any

from pydantic import BaseModel

from src.contextAssembly.contextPackage import ContextPackage
from src.generation.generationResult import GenerationResult
from src.orchestration.workflowMetrics import WorkflowMetrics
from src.planning.executionPlan import ExecutionPlan
from src.response.responseResult import ResponseResult
from src.retrieval.retrievalResult import RetrievalResult
from src.runtimeContext.runtimeContext import RuntimeContext


class WorkflowResult(BaseModel):
    """Immutable final output packaging all planning, contexts, and response metadata."""

    model_config = {"frozen": True}

    response_result: ResponseResult
    execution_plan: ExecutionPlan
    runtime_context: RuntimeContext
    generation_result: GenerationResult | None = None
    retrieval_result: RetrievalResult | None = None
    context_package: ContextPackage | None = None
    execution_metadata: dict[str, Any]
    workflow_metrics: WorkflowMetrics
