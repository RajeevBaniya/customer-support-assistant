from collections.abc import AsyncIterator
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from src.core.appEnvironment import AppEnvironment
from src.realtime.generation_registry import GenerationRegistry, generation_key


def test_generation_key_matches_contract() -> None:
    oid = UUID("11111111-1111-4111-8111-111111111111")
    cid = UUID("22222222-2222-4222-8222-222222222222")
    gid = UUID("33333333-3333-4333-8333-333333333333")
    assert generation_key(organization_id=oid, conversation_id=cid, generation_id=gid) == (
        "recallstack:chat:generation:11111111-1111-4111-8111-111111111111:"
        "22222222-2222-4222-8222-222222222222:33333333-3333-4333-8333-333333333333"
    )


@pytest.mark.asyncio
async def test_register_sets_hash_and_ttl() -> None:
    redis = AsyncMock()
    settings = AppEnvironment(
        APP_ENV="test",
        DEBUG=False,
        DATABASE_URL="postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/recallstack",
        REDIS_STREAM_TTL_SECONDS=120,
    )
    reg = GenerationRegistry(redis, settings)
    oid = UUID("11111111-1111-4111-8111-111111111111")
    cid = UUID("22222222-2222-4222-8222-222222222222")
    gid = UUID("33333333-3333-4333-8333-333333333333")
    uid = UUID("44444444-4444-4444-8444-444444444444")
    await reg.register(
        organization_id=oid,
        conversation_id=cid,
        generation_id=gid,
        user_id=uid,
    )
    redis.hset.assert_awaited_once()
    h_args, h_kwargs = redis.hset.await_args
    assert h_kwargs["mapping"]["user_id"] == str(uid)
    redis.expire.assert_awaited_once_with(
        generation_key(organization_id=oid, conversation_id=cid, generation_id=gid),
        120,
    )


@pytest.mark.asyncio
async def test_cancel_all_marks_cancelled() -> None:
    redis = AsyncMock()
    key = (
        "recallstack:chat:generation:11111111-1111-4111-8111-111111111111:"
        "22222222-2222-4222-8222-222222222222:33333333-3333-4333-8333-333333333333"
    )

    async def scan_iter(*args: object, **kwargs: object) -> AsyncIterator[str]:
        yield key

    redis.scan_iter = scan_iter
    settings = AppEnvironment(
        APP_ENV="test",
        DEBUG=False,
        DATABASE_URL="postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/recallstack",
        REDIS_STREAM_TTL_SECONDS=300,
    )
    reg = GenerationRegistry(redis, settings)
    oid = UUID("11111111-1111-4111-8111-111111111111")
    cid = UUID("22222222-2222-4222-8222-222222222222")
    n = await reg.cancel_all_for_conversation(organization_id=oid, conversation_id=cid)
    assert n == 1
    redis.hset.assert_awaited_once_with(key, "cancelled", "1")
