"""StreamingChatService delivering real-time tokens via server-sent events."""

from __future__ import annotations

import time
from collections.abc import AsyncGenerator
from uuid import UUID, uuid4

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.chatService import ChatService
from src.core.appEnvironment import AppEnvironment
from src.models.userModel import User
from src.orchestration.workflowOrchestrator import WorkflowOrchestrator
from src.orchestration.workflowRequest import WorkflowRequest
from src.realtime.generation_registry import GenerationRegistry
from src.realtime.stream_state import format_sse_event
from src.runtimeTools.conversationTool import (
    AddMessageRequest,
    ConversationTool,
    LoadConversationRequest,
)
from src.runtimeTools.metricsTool import MetricsTool, RecordChatRequest
from src.schemas.chatSchemas import ChatMessageRequest, ChatStreamDoneData
from src.shared.customExceptions import BaseApplicationException, ResourceNotFoundException


class StreamingChatService:
    """Service handling streaming chat sessions and cancellation registry."""

    def __init__(
        self,
        session: AsyncSession,
        settings: AppEnvironment,
        redis_client: Redis,
    ) -> None:
        self._session = session
        self._settings = settings
        self._redis = redis_client
        self._chat = ChatService(session, settings)
        self._conversation_tool = ConversationTool(session, settings)
        self._metrics_tool = MetricsTool(session, settings)

    @classmethod
    def from_request(
        cls,
        session: AsyncSession,
        settings: AppEnvironment,
        redis_client: Redis | None,
    ) -> StreamingChatService:
        """Factory constructor."""
        if redis_client is None:
            raise BaseApplicationException(
                "Redis is required for streaming chat",
                error_code="redis_stream_unavailable",
                status_code=503,
                details={"reason": "redis_url_missing"},
            )
        return cls(session, settings, redis_client)

    async def aclose(self) -> None:
        """Close resources if needed."""
        pass

    async def cancel_generations(self, *, actor: User, conversation_id: UUID) -> int:
        """Cancel all running generations for a conversation."""
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
    ) -> AsyncGenerator[str, None]:
        """Generator delivering real-time tokens, citations, and status messages."""
        self._metrics_tool.record_chat(RecordChatRequest(mode="stream"))
        stream_start_time = time.monotonic()
        registry = GenerationRegistry(self._redis, self._settings)
        deadline = time.monotonic() + float(self._settings.chat_stream_max_duration_seconds)
        generation_id = uuid4()

        try:
            conversation, user_message, _ = await self._chat.attach_user_message(
                actor=actor,
                chat_request=body,
            )
        except BaseApplicationException as exception:
            yield format_sse_event(
                {
                    "type": "error",
                    "data": {
                        "code": exception.error_code,
                        "message": exception.message,
                    },
                }
            )
            return
        except Exception as exception:
            yield format_sse_event(
                {
                    "type": "error",
                    "data": {"code": "stream_attach_failed", "message": str(exception)},
                }
            )
            return

        await registry.register(
            organization_id=actor.organization_id,
            conversation_id=conversation.id,
            generation_id=generation_id,
            user_id=actor.id,
        )
        try:
            orchestrator = WorkflowOrchestrator(self._session, self._settings)
            wf_req = WorkflowRequest(
                user_message=body.message.strip(),
                conversation_id=conversation.id,
                organization_id=actor.organization_id,
                user_id=actor.id,
                selected_document_ids=body.document_ids,
                stream=True,
            )
            parts: list[str] = []
            provider_used = "none"
            final_citations = []

            try:
                async for res in orchestrator.stream_execute(wf_req):
                    provider_used = res.provider_used
                    token_delta = res.assistant_text
                    if res.citations:
                        final_citations = res.citations

                    if await registry.is_cancelled(
                        organization_id=actor.organization_id,
                        conversation_id=conversation.id,
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
                    if token_delta:
                        parts.append(token_delta)
                        yield format_sse_event({"type": "token", "data": {"text": token_delta}})
            except BaseApplicationException as exception:
                yield format_sse_event(
                    {
                        "type": "error",
                        "data": {
                            "code": exception.error_code,
                            "message": exception.message,
                        },
                    }
                )
                return
            except Exception as exception:
                yield format_sse_event(
                    {
                        "type": "error",
                        "data": {"code": "stream_provider_failed", "message": str(exception)},
                    }
                )
                return

            if await registry.is_cancelled(
                organization_id=actor.organization_id,
                conversation_id=conversation.id,
                generation_id=generation_id,
            ):
                yield format_sse_event({"type": "cancelled", "data": {}})
                return

            full_text = "".join(parts)
            citations_json = [
                citation.model_dump(mode="json")
                for citation in final_citations
            ]
            assistant_message = await self._conversation_tool.add_message(
                AddMessageRequest(
                    conversation_id=conversation.id,
                    role="assistant",
                    content=full_text,
                    citations=citations_json,
                )
            )
            await self._conversation_tool.touch_conversation(conversation.id)
            yield format_sse_event(
                {
                    "type": "citations",
                    "data": {"items": citations_json},
                }
            )
            done_data = ChatStreamDoneData(
                generation_id=generation_id,
                conversation_id=conversation.id,
                user_message_id=user_message.id,
                assistant_message_id=assistant_message.id,
                provider=provider_used,
                retrieval_top_k=body.top_k or self._settings.retrieval_default_top_k,
            )
            yield format_sse_event({"type": "done", "data": done_data.model_dump(mode="json")})
        except Exception as exception:
            yield format_sse_event(
                {"type": "error", "data": {"code": "stream_unexpected", "message": str(exception)}}
            )
        finally:
            self._metrics_tool.record_chat_stream_duration(time.monotonic() - stream_start_time)
            await registry.drop_generation(
                organization_id=actor.organization_id,
                conversation_id=conversation.id,
                generation_id=generation_id,
            )
