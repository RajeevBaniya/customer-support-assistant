"""ExecutionPlan combining all planning decisions into a single immutable payload."""

from pydantic import BaseModel

from src.planning.planningModels import (
    ExecutionStrategy,
    RetrievalDecision,
    TokenBudget,
    WorkflowDecision,
)


class ExecutionPlan(BaseModel):
    """Immutable execution plan consumed by the Execution Engine."""

    model_config = {"frozen": True}

    workflow: WorkflowDecision
    retrieval: RetrievalDecision
    budget: TokenBudget
    strategy: ExecutionStrategy
