from __future__ import annotations

from typing import cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.conversations.conversationTitle import conversation_title_from_first_message
from src.conversations.priorTurnsFormat import TurnLine, prior_turns_block
from src.core.appEnvironment import AppEnvironment
from src.models.conversationModel import Conversation
from src.models.messageModel import Message
from src.models.userModel import User
from src.orchestration.workflowOrchestrator import WorkflowOrchestrator
from src.orchestration.workflowRequest import WorkflowRequest
from src.planning.executionPlan import ExecutionPlan
from src.runtimeTools.conversationTool import (
    AddMessageRequest,
    ConversationTool,
    CreateConversationRequest,
    ListConversationsRequest,
    ListMessagesRequest,
    ListRecentMessagesRequest,
    LoadConversationRequest,
)
from src.runtimeTools.metricsTool import MetricsTool, RecordChatRequest
from src.schemas.chatSchemas import (
    ChatMessageRequest,
    ChatMessageResponse,
    ConversationListResponse,
    MessageListResponse,
)
from src.schemas.conversationSchemas import ConversationResponse
from src.schemas.messageSchemas import MessageResponse, MessageRole, citations_from_stored
from src.shared.customExceptions import ResourceNotFoundException


class ChatService:
    """Service handling chat message interactions using conversation and metrics tools."""

    def __init__(self, session: AsyncSession, settings: AppEnvironment) -> None:
        self._session = session
        self._settings = settings
        self._conversation_tool = ConversationTool(session, settings)
        self._metrics_tool = MetricsTool(session, settings)

    @classmethod
    def from_request(cls, session: AsyncSession, settings: AppEnvironment) -> ChatService:
        """Factory constructor."""
        return cls(session, settings)

    async def attach_user_message(
        self,
        *,
        actor: User,
        chat_request: ChatMessageRequest,
        plan: ExecutionPlan | None = None,
    ) -> tuple[Conversation, Message, str | None]:
        """Save an incoming user message, attaching to new or existing conversation."""
        if chat_request.conversation_id is not None:
            conversation = await self._conversation_tool.load_conversation(
                LoadConversationRequest(
                    conversation_id=chat_request.conversation_id,
                    organization_id=actor.organization_id,
                    user_id=actor.id,
                )
            )
            if conversation is None:
                raise ResourceNotFoundException(
                    "Conversation not found",
                    details={"conversation_id": str(chat_request.conversation_id)},
                )
        else:
            conversation = await self._conversation_tool.create_conversation(
                CreateConversationRequest(
                    organization_id=actor.organization_id,
                    user_id=actor.id,
                    title=conversation_title_from_first_message(chat_request.message),
                )
            )

        recent_messages = await self._conversation_tool.list_recent_messages(
            ListRecentMessagesRequest(
                conversation_id=conversation.id,
                limit=self._settings.chat_history_max_messages,
            )
        )
        max_tokens = (
            plan.budget.max_history_tokens
            if plan
            else self._settings.chat_memory_max_tokens
        )
        history_block = prior_turns_block(
            [TurnLine(message.role, message.content) for message in recent_messages],
            max_chars=self._settings.chat_history_max_chars,
            max_tokens=max_tokens,
        )
        memory_text = history_block.strip() or None

        user_message = await self._conversation_tool.add_message(
            AddMessageRequest(
                conversation_id=conversation.id,
                role="user",
                content=chat_request.message.strip(),
                citations=None,
            )
        )
        return conversation, user_message, memory_text

    async def post_message(
        self,
        *,
        actor: User,
        body: ChatMessageRequest,
    ) -> ChatMessageResponse:
        """Process user message by running RAG ask and recording generation results."""
        self._metrics_tool.record_chat(RecordChatRequest(mode="message"))
        conversation, user_message, _ = await self.attach_user_message(
            actor=actor, chat_request=body
        )

        orchestrator = WorkflowOrchestrator(self._session, self._settings)
        wf_req = WorkflowRequest(
            user_message=body.message.strip(),
            conversation_id=conversation.id,
            organization_id=actor.organization_id,
            user_id=actor.id,
            selected_document_ids=body.document_ids,
            stream=False,
        )
        wf_res = await orchestrator.execute(wf_req)
        response_result = wf_res.response_result

        citations_json = [
            citation.model_dump(mode="json")
            for citation in response_result.citations
        ]
        assistant_message = await self._conversation_tool.add_message(
            AddMessageRequest(
                conversation_id=conversation.id,
                role="assistant",
                content=response_result.assistant_text,
                citations=citations_json,
            )
        )
        await self._conversation_tool.touch_conversation(conversation.id)

        top_k_used = 0
        if wf_res.retrieval_result:
            top_k_used = wf_res.retrieval_result.retrieval_metrics.top_k_used

        return ChatMessageResponse(
            conversation_id=conversation.id,
            user_message_id=user_message.id,
            assistant_message_id=assistant_message.id,
            answer=response_result.assistant_text,
            citations=response_result.citations,
            provider=response_result.provider_used,
            retrieval_top_k=top_k_used,
        )

    async def list_conversations(
        self,
        *,
        actor: User,
        limit: int,
        offset: int,
    ) -> ConversationListResponse:
        """Return paginated conversations list for current user."""
        total = await self._conversation_tool.count_conversations(
            organization_id=actor.organization_id,
            user_id=actor.id,
        )
        conversations = await self._conversation_tool.list_conversations(
            ListConversationsRequest(
                organization_id=actor.organization_id,
                user_id=actor.id,
                limit=limit,
                offset=offset,
            )
        )
        response_items = [
            ConversationResponse.model_validate(conversation)
            for conversation in conversations
        ]
        return ConversationListResponse(
            items=response_items, total=total, limit=limit, offset=offset
        )

    async def get_conversation(
        self,
        *,
        actor: User,
        conversation_id: UUID,
    ) -> ConversationResponse:
        """Retrieve a single conversation details."""
        conversation = await self._load_and_verify_conversation(conversation_id, actor)
        return ConversationResponse.model_validate(conversation)

    async def list_messages(
        self,
        *,
        actor: User,
        conversation_id: UUID,
        limit: int,
        offset: int,
    ) -> MessageListResponse:
        """Load message turns paginated in ascending order."""
        conversation = await self._load_and_verify_conversation(conversation_id, actor)
        total = await self._conversation_tool.count_messages(conversation.id)
        messages = await self._conversation_tool.list_messages(
            ListMessagesRequest(conversation_id=conversation.id, limit=limit, offset=offset)
        )
        response_items = [
            MessageResponse(
                id=message.id,
                role=cast(MessageRole, message.role),
                content=message.content,
                citations=citations_from_stored(message.citations),
                created_at=message.created_at,
            )
            for message in messages
        ]
        return MessageListResponse(items=response_items, total=total, limit=limit, offset=offset)

    async def _load_and_verify_conversation(
        self,
        conversation_id: UUID,
        actor: User,
    ) -> Conversation:
        """Retrieve conversation by ID and organization, raising exception if not found."""
        conversation = await self._conversation_tool.load_conversation(
            LoadConversationRequest(
                conversation_id=conversation_id,
                organization_id=actor.organization_id,
                user_id=actor.id,
            )
        )
        if conversation is None:
            raise ResourceNotFoundException(
                "Conversation not found",
                details={"conversation_id": str(conversation_id)},
            )
        return conversation
