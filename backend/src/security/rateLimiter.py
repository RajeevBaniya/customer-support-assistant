import time

import redis.asyncio as redis_async

from src.observability.structuredLogger import get_logger
from src.shared.customExceptions import RateLimitException

_SLIDING_WINDOW_SCRIPT = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local cutoff = now - window * 1000

redis.call('ZREMRANGEBYSCORE', key, '-inf', cutoff)
local count = redis.call('ZCARD', key)

if count >= limit then
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local oldest_score = tonumber(oldest[2]) or now
    local retry_after = math.ceil((oldest_score + window * 1000 - now) / 1000)
    return {0, retry_after}
end

redis.call('ZADD', key, now, now)
redis.call('EXPIRE', key, window + 1)
return {1, 0}
"""

logger = get_logger("security.rate_limiter")


class RateLimiter:
    def __init__(self, client: redis_async.Redis) -> None:
        self._client = client
        self._script = client.register_script(_SLIDING_WINDOW_SCRIPT)

    async def check(
        self,
        *,
        endpoint_key: str,
        org_id: str,
        user_id: str,
        limit: int,
        window_seconds: int,
    ) -> None:
        key = f"rl:{endpoint_key}:{org_id}:{user_id}"
        now_ms = int(time.time() * 1000)

        result = await self._script(
            keys=[key],
            args=[now_ms, window_seconds, limit],
        )

        allowed = int(result[0])
        retry_after = int(result[1])

        if not allowed:
            logger.warning(
                "rate_limit_exceeded",
                endpoint=endpoint_key,
                org_id=org_id,
                user_id=user_id,
                retry_after_seconds=retry_after,
            )
            raise RateLimitException(retry_after=retry_after)
