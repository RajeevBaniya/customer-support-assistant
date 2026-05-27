from uuid import UUID

from pydantic import Field

from src.schemas.commonSchemas import ApiModel
from src.schemas.conversationSchemas import ConversationResponse
from src.schemas.messageSchemas import MessageResponse
from src.schemas.ragSchemas import CitationItem


class ChatMessageRequest(ApiModel):
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: UUID | None = None
    document_ids: list[UUID] | None = None
    top_k: int | None = Field(default=None, ge=1, le=50)


class ChatMessageResponse(ApiModel):
    conversation_id: UUID
    user_message_id: UUID
    assistant_message_id: UUID
    answer: str
    citations: list[CitationItem]
    provider: str
    retrieval_top_k: int


class ConversationListResponse(ApiModel):
    items: list[ConversationResponse]
    total: int
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)


class MessageListResponse(ApiModel):
    items: list[MessageResponse]
    total: int
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)


class ChatStreamDoneData(ApiModel):
    generation_id: UUID
    conversation_id: UUID
    user_message_id: UUID
    assistant_message_id: UUID
    provider: str
    retrieval_top_k: int
