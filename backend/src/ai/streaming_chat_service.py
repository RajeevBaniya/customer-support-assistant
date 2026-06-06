import time
from collections.abc import AsyncIterator
from uuid import UUID, uuid4

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.chatService import ChatService
from src.ai.providerRouter import stream_chat_with_fallback
from src.ai.ragService import RagService
from src.conversations.conversationRepository import ConversationRepository
from src.conversations.messageRepository import MessageRepository
from src.core.appEnvironment import AppEnvironment
from src.models.messageModel import Message
from src.models.userModel import User
from src.observability.metrics.recorders import record_chat_request, record_chat_stream_duration
from src.realtime.generation_registry import GenerationRegistry
from src.realtime.stream_state import format_sse_event
from src.schemas.chatSchemas import ChatMessageRequest, ChatStreamDoneData
from src.schemas.retrievalSchemas import RetrievalSearchRequest
from src.shared.customExceptions import BaseApplicationException, ResourceNotFoundException


class StreamingChatService:
    def __init__(
        self,
        session: AsyncSession,
        settings: AppEnvironment,
        redis_client: Redis,
    ) -> None:
        self._session = session
        self._settings = settings
        self._redis = redis_client
        self._chat = ChatService.from_request(session, settings)
        self._rag = RagService.from_request(session, settings)
        self._conversations = ConversationRepository(session)
        self._messages = MessageRepository(session)

    @classmethod
    def from_request(
        cls,
        session: AsyncSession,
        settings: AppEnvironment,
        redis_client: Redis | None,
    ) -> "StreamingChatService":
        if redis_client is None:
            raise BaseApplicationException(
                "Redis is required for streaming chat",
                error_code="redis_stream_unavailable",
                status_code=503,
                details={"reason": "redis_url_missing"},
            )
        return cls(session, settings, redis_client)

    async def aclose(self) -> None:
        pass

    async def cancel_generations(self, *, actor: User, conversation_id: UUID) -> int:
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
        registry = GenerationRegistry(self._redis, self._settings)
        return await registry.cancel_all_for_conversation(
            organization_id=actor.organization_id,
            conversation_id=conversation_id,
        )

    async def iter_chat_sse(
        self,
        *,
        actor: User,
        body: ChatMessageRequest,
    ) -> AsyncIterator[str]:
        generation_id = uuid4()
        record_chat_request(mode="stream")
        stream_t0 = time.monotonic()
        registry = GenerationRegistry(self._redis, self._settings)
        deadline = time.monotonic() + float(self._settings.chat_stream_max_duration_seconds)

        try:
            conv, user_row, memory_text = await self._chat.attach_user_message(
                actor=actor,
                body=body,
            )
        except BaseApplicationException as exc:
            yield format_sse_event(
                {"type": "error", "data": {"code": exc.error_code, "message": exc.message}}
            )
            return
        except Exception as exc:
            yield format_sse_event(
                {
                    "type": "error",
                    "data": {"code": "stream_attach_failed", "message": str(exc)},
                }
            )
            return

        await registry.register(
            organization_id=actor.organization_id,
            conversation_id=conv.id,
            generation_id=generation_id,
            user_id=actor.id,
        )
        try:
            try:
                prep = await self._rag.prepare_stream_prompt(
                    organization_id=actor.organization_id,
                    body=RetrievalSearchRequest(
                        query=body.message.strip(),
                        top_k=body.top_k,
                        document_ids=body.document_ids,
                    ),
                    prior_turns_text=memory_text,
                )
            except BaseApplicationException as exc:
                yield format_sse_event(
                    {
                        "type": "error",
                        "data": {"code": exc.error_code, "message": exc.message},
                    }
                )
                return
            except Exception as exc:
                yield format_sse_event(
                    {
                        "type": "error",
                        "data": {"code": "stream_prepare_failed", "message": str(exc)},
                    }
                )
                return

            if not prep.use_llm:
                text = prep.fixed_reply or ""
                if text:
                    yield format_sse_event({"type": "token", "data": {"text": text}})
                assistant = Message(
                    conversation_id=conv.id,
                    role="assistant",
                    content=text,
                    citations=[],
                )
                await self._messages.add(assistant)
                await self._conversations.touch_updated_at(conv.id)
                yield format_sse_event(
                    {
                        "type": "citations",
                        "data": {"items": []},
                    }
                )
                done = ChatStreamDoneData(
                    generation_id=generation_id,
                    conversation_id=conv.id,
                    user_message_id=user_row.id,
                    assistant_message_id=assistant.id,
                    provider="none",
                    retrieval_top_k=prep.top_k,
                )
                yield format_sse_event({"type": "done", "data": done.model_dump(mode="json")})
                return

            parts: list[str] = []
            provider_used = "none"
            try:
                async for prov, delta in stream_chat_with_fallback(
                    self._settings,
                    system=prep.system,
                    user=prep.user,
                    organization_id=actor.organization_id,
                    route_type="chat_stream",
                ):
                    provider_used = prov
                    if await registry.is_cancelled(
                        organization_id=actor.organization_id,
                        conversation_id=conv.id,
                        generation_id=generation_id,
                    ):
                        yield format_sse_event({"type": "cancelled", "data": {}})
                        return
                    if time.monotonic() > deadline:
                        yield format_sse_event(
                            {
                                "type": "error",
                                "data": {
                                    "code": "stream_max_duration",
                                    "message": "stream timed out",
                                },
                            }
                        )
                        return
                    if delta:
                        parts.append(delta)
                        yield format_sse_event({"type": "token", "data": {"text": delta}})
            except BaseApplicationException as exc:
                yield format_sse_event(
                    {"type": "error", "data": {"code": exc.error_code, "message": exc.message}}
                )
                return
            except Exception as exc:
                yield format_sse_event(
                    {
                        "type": "error",
                        "data": {"code": "stream_provider_failed", "message": str(exc)},
                    }
                )
                return

            if await registry.is_cancelled(
                organization_id=actor.organization_id,
                conversation_id=conv.id,
                generation_id=generation_id,
            ):
                yield format_sse_event({"type": "cancelled", "data": {}})
                return

            full_text = "".join(parts)
            cite_json = [c.model_dump(mode="json") for c in prep.citations]
            assistant = Message(
                conversation_id=conv.id,
                role="assistant",
                content=full_text,
                citations=cite_json,
            )
            await self._messages.add(assistant)
            await self._conversations.touch_updated_at(conv.id)
            yield format_sse_event(
                {
                    "type": "citations",
                    "data": {"items": [c.model_dump(mode="json") for c in prep.citations]},
                }
            )
            done = ChatStreamDoneData(
                generation_id=generation_id,
                conversation_id=conv.id,
                user_message_id=user_row.id,
                assistant_message_id=assistant.id,
                provider=provider_used,
                retrieval_top_k=prep.top_k,
            )
            yield format_sse_event({"type": "done", "data": done.model_dump(mode="json")})
        except Exception as exc:
            yield format_sse_event(
                {"type": "error", "data": {"code": "stream_unexpected", "message": str(exc)}}
            )
        finally:
            record_chat_stream_duration(time.monotonic() - stream_t0)
            await registry.drop_generation(
                organization_id=actor.organization_id,
                conversation_id=conv.id,
                generation_id=generation_id,
            )
