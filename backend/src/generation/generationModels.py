from uuid import UUID

from pydantic import BaseModel, Field

from src.contextAssembly.contextPackage import ContextPackage


class GenerationRequest(BaseModel):
    """Prised request model for LLM generation execution."""

    model_config = {"frozen": True}

    context_package: ContextPackage
    organization_id: UUID | None = None
    stream: bool = False
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    max_output_tokens: int | None = Field(default=None, ge=1)
    is_evaluation: bool = False
