from datetime import datetime
from uuid import UUID

from src.schemas.commonSchemas import ApiModel


class ConversationResponse(ApiModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
