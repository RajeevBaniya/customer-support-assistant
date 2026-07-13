"""Strongly typed immutable planning models for representing planning decisions."""

from uuid import UUID

from pydantic import BaseModel, Field


class WorkflowDecision(BaseModel):
    """Immutable model representing the routing decision for workflows."""

    model_config = {"frozen": True}

    selected_workflow: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class MetadataFilter(BaseModel):
    """Immutable provider-agnostic model scoping organization and document identifiers."""

    model_config = {"frozen": True}

    organization_id: UUID
    document_ids: list[UUID] | None = None


class RetrievalDecision(BaseModel):
    """Immutable model representing semantic search decisions."""

    model_config = {"frozen": True}

    need_retrieval: bool
    retrieval_mode: str = Field(min_length=1)
    metadata_filter: MetadataFilter | None = None


class TokenBudget(BaseModel):
    """Immutable model representing resource and context memory size limits."""

    model_config = {"frozen": True}

    max_context_tokens: int
    max_history_tokens: int


class ExecutionStrategy(BaseModel):
    """Immutable model representing processing rules and concurrency behavior."""

    model_config = {"frozen": True}

    concurrency: str = Field(min_length=1)
