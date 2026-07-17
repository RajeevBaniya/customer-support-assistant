"""ExecutionPlan combining all planning decisions into a single immutable payload."""

from typing import Any

from pydantic import BaseModel, Field

from src.planning.planningModels import (
    ExecutionStrategy,
    RetrievalDecision,
    TokenBudget,
    WorkflowDecision,
)


class ExecutionPlan(BaseModel):
    """Immutable execution plan consumed by the Execution Engine."""

    model_config = {"frozen": True}

    # Agentic RAG planning fields (with defaults for backward compatibility)
    user_intent: str = "question"
    execution_type: str = "rag"
    complexity: str = "low"
    retrieval_required: bool = True
    retrieval_strategy: str = "semantic"
    history_required: bool = False
    context_required: bool = True
    multiple_retrieval_passes: bool = False
    reviewer_enabled: bool = False
    tool_usage_beneficial: bool = False
    estimated_steps: int = 1
    confidence: float = 1.0
    planner_metadata: dict[str, Any] = Field(default_factory=dict)

    # Legacy fields kept for downstream engine compatibility
    workflow: WorkflowDecision
    retrieval: RetrievalDecision
    budget: TokenBudget
    strategy: ExecutionStrategy
