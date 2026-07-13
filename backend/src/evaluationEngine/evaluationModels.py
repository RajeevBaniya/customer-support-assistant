from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class EvaluationRequest(BaseModel):
    model_config = {"frozen": True}

    query: str
    reference_answer: str | None = None
    organization_id: UUID
    user_id: UUID
    document_ids: list[UUID] | None = None
    top_k: int | None = None
    prior_turns_text: str | None = None

class EvaluationDatasetRequest(BaseModel):
    model_config = {"frozen": True}

    dataset_id: UUID
    organization_id: UUID
    user_id: UUID
