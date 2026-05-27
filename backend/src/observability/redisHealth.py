import asyncio
from collections.abc import Awaitable
from typing import cast

from src.core.appEnvironment import AppEnvironment
from src.realtime.redis_connection import create_async_redis_client


async def redis_health(settings: AppEnvironment) -> dict[str, object]:
    url = settings.redis_url
    if url is None or not str(url).strip():
        return {
            "redis_configured": False,
            "redis_reachable": False,
            "streaming_ready": False,
        }
    client = await create_async_redis_client(str(url))
    try:

        async def _ping() -> bool:
            res = await cast(Awaitable[bool], client.ping())
            return bool(res)

        await asyncio.wait_for(_ping(), timeout=3.0)
        ok = True
    except Exception:
        ok = False
    finally:
        await client.aclose()
    return {
        "redis_configured": True,
        "redis_reachable": ok,
        "streaming_ready": ok,
    }
