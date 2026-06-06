from urllib.parse import urlparse, urlunparse

import redis.asyncio as redis_async


def normalize_redis_url_for_tls(url: str) -> str:
    stripped = url.strip()
    if not stripped:
        return stripped
    parsed = urlparse(stripped)
    host = (parsed.hostname or "").lower()
    if parsed.scheme == "redis" and host.endswith(".upstash.io"):
        return urlunparse(parsed._replace(scheme="rediss"))
    return stripped


def build_redis_client(url: str) -> redis_async.Redis:
    normalized = normalize_redis_url_for_tls(url)
    return redis_async.Redis.from_url(normalized, decode_responses=True)


async def create_async_redis_client(url: str) -> redis_async.Redis:
    return build_redis_client(url)
