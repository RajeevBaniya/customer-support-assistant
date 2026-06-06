from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.chatService import ChatService
from src.ai.streaming_chat_service import StreamingChatService
from src.auth.userAccess import get_application_user
from src.core.appEnvironment import AppEnvironment
from src.database.databaseSession import get_db_session
from src.models.userModel import User
from src.schemas.chatSchemas import ChatMessageRequest
from src.security.rateLimitDependency import rate_limited
from src.shared.responseFormatter import format_success_response

chat_router = APIRouter(prefix="/chat", tags=["chat"])

_rate_limit_message = rate_limited("chat_message", lambda s: s.rate_limit_chat_message)
_rate_limit_stream = rate_limited("chat_stream", lambda s: s.rate_limit_chat_stream)


@chat_router.post("/message", dependencies=[Depends(_rate_limit_message)])
async def post_chat_message(
    request: Request,
    body: ChatMessageRequest,
    user: User = Depends(get_application_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    settings: AppEnvironment = request.app.state.settings
    service = ChatService.from_request(session, settings)
    payload = await service.post_message(actor=user, body=body)
    out = format_success_response(payload.model_dump(mode="json"), message="Chat")
    return JSONResponse(content=out)


@chat_router.post("/stream", dependencies=[Depends(_rate_limit_stream)])
async def stream_chat_message(
    request: Request,
    body: ChatMessageRequest,
    user: User = Depends(get_application_user),
    session: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    settings: AppEnvironment = request.app.state.settings
    svc = await StreamingChatService.create(session, settings)

    async def event_gen() -> AsyncIterator[bytes]:
        try:
            async for line in svc.iter_chat_sse(actor=user, body=body):
                yield line.encode("utf-8")
        finally:
            await svc.aclose()

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@chat_router.post("/conversations/{conversation_id}/cancel")
async def cancel_chat_stream_generations(
    request: Request,
    conversation_id: UUID,
    user: User = Depends(get_application_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    settings: AppEnvironment = request.app.state.settings
    svc = await StreamingChatService.create(session, settings)
    try:
        count = await svc.cancel_generations(actor=user, conversation_id=conversation_id)
    finally:
        await svc.aclose()
    out = format_success_response(
        {"cancelled_generations": count},
        message="Chat stream cancel",
    )
    return JSONResponse(content=out)


@chat_router.get("/conversations")
async def list_chat_conversations(
    request: Request,
    user: User = Depends(get_application_user),
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> Response:
    settings: AppEnvironment = request.app.state.settings
    service = ChatService.from_request(session, settings)
    payload = await service.list_conversations(actor=user, limit=limit, offset=offset)
    out = format_success_response(payload.model_dump(mode="json"), message="Conversations")
    return JSONResponse(content=out)


@chat_router.get("/conversations/{conversation_id}")
async def get_chat_conversation(
    request: Request,
    conversation_id: UUID,
    user: User = Depends(get_application_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    settings: AppEnvironment = request.app.state.settings
    service = ChatService.from_request(session, settings)
    payload = await service.get_conversation(actor=user, conversation_id=conversation_id)
    out = format_success_response(payload.model_dump(mode="json"), message="Conversation")
    return JSONResponse(content=out)


@chat_router.get("/conversations/{conversation_id}/messages")
async def list_chat_messages(
    request: Request,
    conversation_id: UUID,
    user: User = Depends(get_application_user),
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> Response:
    settings: AppEnvironment = request.app.state.settings
    service = ChatService.from_request(session, settings)
    payload = await service.list_messages(
        actor=user,
        conversation_id=conversation_id,
        limit=limit,
        offset=offset,
    )
    out = format_success_response(payload.model_dump(mode="json"), message="Messages")
    return JSONResponse(content=out)
