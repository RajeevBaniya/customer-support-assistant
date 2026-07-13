"""ConversationTool managing conversation history database mapping."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from src.conversations.conversationRepository import ConversationRepository
from src.conversations.messageRepository import MessageRepository
from src.models.conversationModel import Conversation
from src.models.messageModel import Message
from src.runtimeTools.baseTool import BaseTool


class LoadConversationRequest(BaseModel):
    """Schema for loading a specific user conversation."""

    conversation_id: UUID
    organization_id: UUID
    user_id: UUID


class CreateConversationRequest(BaseModel):
    """Schema for creating a new conversation."""

    organization_id: UUID
    user_id: UUID
    title: str | None = None


class ListConversationsRequest(BaseModel):
    """Schema for listing recent conversations."""

    organization_id: UUID
    user_id: UUID
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)


class AddMessageRequest(BaseModel):
    """Schema for saving a conversation turn message."""

    conversation_id: UUID
    role: str = Field(min_length=1)
    content: str = Field(min_length=1)
    token_count: int | None = None
    citations: list[dict[str, Any]] | None = None


class ListMessagesRequest(BaseModel):
    """Schema for loading conversation message history."""

    conversation_id: UUID
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)


class ListRecentMessagesRequest(BaseModel):
    """Schema for loading recent messages for context memory."""

    conversation_id: UUID
    limit: int = Field(ge=1, le=100)


class ConversationTool(BaseTool):
    """Conversation history and message turns persistence tool."""

    async def load_conversation(
        self, request: LoadConversationRequest
    ) -> Conversation | None:
        """Load a single conversation."""
        repository = ConversationRepository(self._session)
        return await repository.get_for_user(
            request.conversation_id,
            organization_id=request.organization_id,
            user_id=request.user_id,
        )

    async def create_conversation(
        self, request: CreateConversationRequest
    ) -> Conversation:
        """Create and store a new conversation."""
        repository = ConversationRepository(self._session)
        conversation = Conversation(
            organization_id=request.organization_id,
            user_id=request.user_id,
            title=request.title,
        )
        return await repository.add(conversation)

    async def list_conversations(
        self, request: ListConversationsRequest
    ) -> list[Conversation]:
        """List recent conversations for a user."""
        repository = ConversationRepository(self._session)
        return await repository.list_for_user(
            organization_id=request.organization_id,
            user_id=request.user_id,
            limit=request.limit,
            offset=request.offset,
        )

    async def count_conversations(
        self, organization_id: UUID, user_id: UUID
    ) -> int:
        """Count total conversations for a user."""
        repository = ConversationRepository(self._session)
        return await repository.count_for_user(
            organization_id=organization_id,
            user_id=user_id,
        )

    async def touch_conversation(self, conversation_id: UUID) -> None:
        """Update updated_at timestamp on a conversation."""
        repository = ConversationRepository(self._session)
        await repository.touch_updated_at(conversation_id)

    async def add_message(self, request: AddMessageRequest) -> Message:
        """Save a message turn."""
        repository = MessageRepository(self._session)
        message = Message(
            conversation_id=request.conversation_id,
            role=request.role,
            content=request.content,
            citations=request.citations,
        )
        return await repository.add(message)

    async def list_messages(
        self, request: ListMessagesRequest
    ) -> list[Message]:
        """List messages in chronological order."""
        repository = MessageRepository(self._session)
        return await repository.list_page_asc(
            request.conversation_id,
            limit=request.limit,
            offset=request.offset,
        )

    async def list_recent_messages(
        self, request: ListRecentMessagesRequest
    ) -> list[Message]:
        """List recent messages in descending order."""
        repository = MessageRepository(self._session)
        return await repository.list_recent_desc(
            request.conversation_id,
            limit=request.limit,
        )

    async def count_messages(self, conversation_id: UUID) -> int:
        """Count total messages in a conversation."""
        repository = MessageRepository(self._session)
        return await repository.count_for_conversation(conversation_id)
