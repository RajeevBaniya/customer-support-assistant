"""Immutable ContextPackage combining all assembled contexts for the generation layer."""

from pydantic import BaseModel

from src.contextAssembly.contextAssemblyModels import (
    CitationContext,
    ConversationContext,
    ExecutionMetadata,
    RetrievedContext,
    SystemInstructions,
    WorkspaceContext,
)


class ContextPackage(BaseModel):
    """Prised immutable payload consumed directly by generation providers."""

    model_config = {"frozen": True}

    conversation: ConversationContext
    retrieved: RetrievedContext
    workspace: WorkspaceContext
    metadata: ExecutionMetadata
    instructions: SystemInstructions
    citations: CitationContext
