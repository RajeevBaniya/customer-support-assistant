"""Immutable Pydantic models for context assembly output."""

from uuid import UUID

from pydantic import BaseModel

from src.schemas.ragSchemas import CitationItem
from src.schemas.retrievalSchemas import RetrievalChunkItem


class ConversationContext(BaseModel):
    """Assembled conversation history context."""

    model_config = {"frozen": True}

    prior_turns_text: str | None = None
    message_count: int


class RetrievedContext(BaseModel):
    """Assembled retrieved knowledge chunks."""

    model_config = {"frozen": True}

    context_text: str
    truncated: bool
    capped_items: list[RetrievalChunkItem]
    chunk_count: int


class WorkspaceContext(BaseModel):
    """Assembled workspace scoping context."""

    model_config = {"frozen": True}

    document_ids: list[UUID]


class ExecutionMetadata(BaseModel):
    """Assembled metadata parameters for execution tracking."""

    model_config = {"frozen": True}

    query: str
    top_k: int
    selected_workflow: str
    retrieval_mode: str
    concurrency: str


class SystemInstructions(BaseModel):
    """Assembled instructions and prompts for generation layer."""

    model_config = {"frozen": True}

    system_prompt: str
    user_prompt: str


class CitationContext(BaseModel):
    """Assembled citation metadata and distinct source count."""

    model_config = {"frozen": True}

    citations: list[CitationItem]
    source_count: int
