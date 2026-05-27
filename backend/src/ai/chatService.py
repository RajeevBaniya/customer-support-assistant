from typing import cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.ragService import RagService
from src.conversations.conversationRepository import ConversationRepository
from src.conversations.conversationTitle import conversation_title_from_first_message
from src.conversations.messageRepository import MessageRepository
from src.conversations.priorTurnsFormat import TurnLine, prior_turns_block
from src.core.appEnvironment import AppEnvironment
from src.models.conversationModel import Conversation
from src.models.messageModel import Message
from src.models.userModel import User
from src.schemas.chatSchemas import (
    ChatMessageRequest,
    ChatMessageResponse,
    ConversationListResponse,
    MessageListResponse,
)
from src.schemas.conversationSchemas import ConversationResponse
from src.schemas.messageSchemas import MessageResponse, MessageRole, citations_from_stored
from src.schemas.retrievalSchemas import RetrievalSearchRequest
from src.shared.customExceptions import ResourceNotFoundException


class ChatService:
    def __init__(self, session: AsyncSession, settings: AppEnvironment) -> None:
        self._session = session
        self._settings = settings
        self._conversations = ConversationRepository(session)
        self._messages = MessageRepository(session)

    @classmethod
    def from_request(cls, session: AsyncSession, settings: AppEnvironment) -> "ChatService":
        return cls(session, settings)

    async def attach_user_message(
        self,
        *,
        actor: User,
        body: ChatMessageRequest,
    ) -> tuple[Conversation, Message, str | None]:
        if body.conversation_id is not None:
            conv = await self._conversations.get_for_user(
                body.conversation_id,
                organization_id=actor.organization_id,
                user_id=actor.id,
            )
            if conv is None:
                raise ResourceNotFoundException(
                    "Conversation not found",
                    details={"conversation_id": str(body.conversation_id)},
                )
        else:
            conv = Conversation(
                organization_id=actor.organization_id,
                user_id=actor.id,
                title=conversation_title_from_first_message(body.message),
            )
            await self._conversations.add(conv)

        prior = await self._messages.list_recent_desc(
            conv.id,
            limit=self._settings.chat_history_max_messages,
        )
        memory = prior_turns_block(
            [TurnLine(m.role, m.content) for m in prior],
            self._settings.chat_history_max_chars,
        )
        memory_text = memory.strip() or None

        user_row = Message(
            conversation_id=conv.id,
            role="user",
            content=body.message.strip(),
            citations=None,
        )
        await self._messages.add(user_row)
        return conv, user_row, memory_text

    async def post_message(self, *, actor: User, body: ChatMessageRequest) -> ChatMessageResponse:
        conv, user_row, memory_text = await self.attach_user_message(actor=actor, body=body)

        rag = RagService.from_request(self._session, self._settings)
        retrieval_body = RetrievalSearchRequest(
            query=body.message.strip(),
            top_k=body.top_k,
            document_ids=body.document_ids,
        )
        out = await rag.ask(
            organization_id=actor.organization_id,
            body=retrieval_body,
            prior_turns_text=memory_text,
        )

        cite_json = [c.model_dump(mode="json") for c in out.citations]
        assistant_row = Message(
            conversation_id=conv.id,
            role="assistant",
            content=out.answer,
            citations=cite_json,
        )
        await self._messages.add(assistant_row)
        await self._conversations.touch_updated_at(conv.id)

        return ChatMessageResponse(
            conversation_id=conv.id,
            user_message_id=user_row.id,
            assistant_message_id=assistant_row.id,
            answer=out.answer,
            citations=out.citations,
            provider=out.provider,
            retrieval_top_k=out.retrieval_top_k,
        )

    async def list_conversations(
        self,
        *,
        actor: User,
        limit: int,
        offset: int,
    ) -> ConversationListResponse:
        total = await self._conversations.count_for_user(
            organization_id=actor.organization_id,
            user_id=actor.id,
        )
        rows = await self._conversations.list_for_user(
            organization_id=actor.organization_id,
            user_id=actor.id,
            limit=limit,
            offset=offset,
        )
        items = [ConversationResponse.model_validate(r) for r in rows]
        return ConversationListResponse(items=items, total=total, limit=limit, offset=offset)

    async def get_conversation(self, *, actor: User, conversation_id: UUID) -> ConversationResponse:
        row = await self._conversations.get_for_user(
            conversation_id,
            organization_id=actor.organization_id,
            user_id=actor.id,
        )
        if row is None:
            raise ResourceNotFoundException(
                "Conversation not found",
                details={"conversation_id": str(conversation_id)},
            )
        return ConversationResponse.model_validate(row)

    async def list_messages(
        self,
        *,
        actor: User,
        conversation_id: UUID,
        limit: int,
        offset: int,
    ) -> MessageListResponse:
        conv = await self._conversations.get_for_user(
            conversation_id,
            organization_id=actor.organization_id,
            user_id=actor.id,
        )
        if conv is None:
            raise ResourceNotFoundException(
                "Conversation not found",
                details={"conversation_id": str(conversation_id)},
            )
        total = await self._messages.count_for_conversation(conversation_id)
        rows = await self._messages.list_page_asc(conversation_id, limit=limit, offset=offset)
        items = [
            MessageResponse(
                id=r.id,
                role=cast(MessageRole, r.role),
                content=r.content,
                citations=citations_from_stored(r.citations),
                created_at=r.created_at,
            )
            for r in rows
        ]
        return MessageListResponse(items=items, total=total, limit=limit, offset=offset)
