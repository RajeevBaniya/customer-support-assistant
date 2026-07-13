"""RetrievalRequest model containing planning contexts and query configurations."""

from uuid import UUID

from pydantic import BaseModel, Field

from src.planning.executionPlan import ExecutionPlan
from src.runtimeContext.runtimeContext import RuntimeContext


class RetrievalRequest(BaseModel):
    """Prised request model for executing semantic retrieval query."""

    model_config = {"frozen": True}

    execution_plan: ExecutionPlan
    runtime_context: RuntimeContext
    organization_id: UUID
    query: str
    top_k: int | None = Field(default=None, ge=1)
    retrieval_mode: str | None = Field(default=None, min_length=1)
