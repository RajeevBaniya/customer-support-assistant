"""ResponseRequest model containing generation outputs and planning packages."""

from pydantic import BaseModel

from src.contextAssembly.contextPackage import ContextPackage
from src.generation.generationResult import GenerationResult
from src.planning.executionPlan import ExecutionPlan
from src.runtimeContext.runtimeContext import RuntimeContext


class ResponseRequest(BaseModel):
    """Prised request model for executing response compilation."""

    model_config = {"frozen": True}

    generation_result: GenerationResult
    context_package: ContextPackage
    execution_plan: ExecutionPlan | None = None
    runtime_context: RuntimeContext | None = None
