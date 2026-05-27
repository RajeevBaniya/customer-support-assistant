from datetime import datetime
from typing import Literal
from uuid import UUID

from src.schemas.commonSchemas import ApiModel
from src.schemas.ragSchemas import CitationItem

MessageRole = Literal["user", "assistant"]


class MessageResponse(ApiModel):
    id: UUID
    role: MessageRole
    content: str
    citations: list[CitationItem] | None = None
    created_at: datetime


def citations_from_stored(raw: object | None) -> list[CitationItem] | None:
    if raw is None:
        return None
    if isinstance(raw, list) and not raw:
        return []
    if isinstance(raw, list):
        return [CitationItem.model_validate(item) for item in raw]
    return None
