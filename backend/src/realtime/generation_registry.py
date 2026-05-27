from collections.abc import Awaitable
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from redis.asyncio import Redis

from src.core.appEnvironment import AppEnvironment


def generation_key(
    *,
    organization_id: UUID,
    conversation_id: UUID,
    generation_id: UUID,
) -> str:
    return f"recallstack:chat:generation:{organization_id}:{conversation_id}:{generation_id}"


def generation_prefix_for_conversation(*, organization_id: UUID, conversation_id: UUID) -> str:
    return f"recallstack:chat:generation:{organization_id}:{conversation_id}:*"


class GenerationRegistry:
    def __init__(self, client: Redis, settings: AppEnvironment) -> None:
        self._r = client
        self._ttl = int(settings.redis_stream_ttl_seconds)

    async def register(
        self,
        *,
        organization_id: UUID,
        conversation_id: UUID,
        generation_id: UUID,
        user_id: UUID,
    ) -> None:
        key = generation_key(
            organization_id=organization_id,
            conversation_id=conversation_id,
            generation_id=generation_id,
        )
        now = datetime.now(UTC).isoformat()
        await cast(
            Awaitable[int],
            self._r.hset(
                key,
                mapping={
                    "user_id": str(user_id),
                    "conversation_id": str(conversation_id),
                    "organization_id": str(organization_id),
                    "cancelled": "0",
                    "started_at": now,
                },
            ),
        )
        await cast(Awaitable[bool], self._r.expire(key, self._ttl))

    async def is_cancelled(
        self,
        *,
        organization_id: UUID,
        conversation_id: UUID,
        generation_id: UUID,
    ) -> bool:
        key = generation_key(
            organization_id=organization_id,
            conversation_id=conversation_id,
            generation_id=generation_id,
        )
        raw = await cast(Awaitable[str | None], self._r.hget(key, "cancelled"))
        return bool(raw == "1")

    async def cancel_all_for_conversation(
        self,
        *,
        organization_id: UUID,
        conversation_id: UUID,
    ) -> int:
        pattern = generation_prefix_for_conversation(
            organization_id=organization_id,
            conversation_id=conversation_id,
        )
        updated = 0
        async for key in self._r.scan_iter(match=pattern):
            await cast(Awaitable[int], self._r.hset(key, "cancelled", "1"))
            await cast(Awaitable[bool], self._r.expire(key, self._ttl))
            updated += 1
        return updated

    async def drop_generation(
        self,
        *,
        organization_id: UUID,
        conversation_id: UUID,
        generation_id: UUID,
    ) -> None:
        key = generation_key(
            organization_id=organization_id,
            conversation_id=conversation_id,
            generation_id=generation_id,
        )
        await cast(Awaitable[int], self._r.delete(key))
