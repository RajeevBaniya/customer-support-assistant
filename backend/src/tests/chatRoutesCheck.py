from uuid import UUID

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_chat_message_requires_auth(async_client: AsyncClient) -> None:
    response = await async_client.post(
        "/api/v1/chat/message",
        json={"message": "hello there"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_chat_conversations_list_requires_auth(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/chat/conversations")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_chat_conversation_get_requires_auth(async_client: AsyncClient) -> None:
    cid = UUID("00000000-0000-4000-8000-000000000001")
    response = await async_client.get(f"/api/v1/chat/conversations/{cid}")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_chat_messages_list_requires_auth(async_client: AsyncClient) -> None:
    cid = UUID("00000000-0000-4000-8000-000000000002")
    response = await async_client.get(f"/api/v1/chat/conversations/{cid}/messages")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_chat_stream_requires_auth(async_client: AsyncClient) -> None:
    response = await async_client.post(
        "/api/v1/chat/stream",
        json={"message": "hello"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_chat_stream_cancel_requires_auth(async_client: AsyncClient) -> None:
    cid = UUID("00000000-0000-4000-8000-000000000003")
    response = await async_client.post(f"/api/v1/chat/conversations/{cid}/cancel")
    assert response.status_code == 401
