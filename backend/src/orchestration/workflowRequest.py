"""WorkflowRequest model containing input context variables."""

from uuid import UUID

from pydantic import BaseModel


class WorkflowRequest(BaseModel):
    """Prised request model for executing the entire RAG orchestration pipeline."""

    model_config = {"frozen": True}

    user_message: str
    conversation_id: UUID | None = None
    organization_id: UUID
    user_id: UUID
    selected_document_ids: list[UUID] | None = None
    stream: bool = False
    evaluation_mode: bool = False
    provider_override: str | None = None
