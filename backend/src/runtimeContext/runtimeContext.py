"""Strongly-typed Pydantic models representing the RuntimeContext."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ContextMessage(BaseModel):
    """Pydantic model representing a conversation message turn in context."""

    id: UUID
    role: str
    content: str
    citations: list[dict[str, Any]] | None = None
    created_at: datetime


class ConversationContext(BaseModel):
    """Context model enclosing conversation state and message history."""

    conversation_id: UUID
    title: str
    recent_messages: list[ContextMessage] = Field(default_factory=list)


class ContextDocument(BaseModel):
    """Context model enclosing workspace document metadata details."""

    id: UUID
    original_file_name: str
    mime_type: str
    file_size: int
    upload_status: str
    parsing_status: str
    embedding_status: str
    created_at: datetime


class WorkspaceContext(BaseModel):
    """Context model enclosing active workspace document attachments."""

    selected_documents: list[ContextDocument] = Field(default_factory=list)


class SessionContext(BaseModel):
    """Context model enclosing organization, user identity, and RBAC roles."""

    organization_id: UUID
    organization_name: str
    user_id: UUID
    email_address: str
    first_name: str | None = None
    last_name: str | None = None
    roles: list[str] = Field(default_factory=list)


class ExecutionContext(BaseModel):
    """Context model enclosing runtime configurations and execution parameters."""

    query: str
    top_k: int
    document_ids: list[UUID] | None = None
    enable_original_file_storage: bool
    hybrid_retrieval_enabled: bool
    active_llm_provider: str
    embedding_model: str
    chat_history_max_messages: int


class RuntimeContext(BaseModel):
    """Unified context object containing all state collected prior to planning."""

    conversation: ConversationContext | None = None
    session: SessionContext
    workspace: WorkspaceContext
    execution: ExecutionContext
