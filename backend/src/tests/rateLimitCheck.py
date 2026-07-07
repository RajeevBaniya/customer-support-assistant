import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.security.rateLimiter import RateLimiter
from src.shared.customExceptions import RateLimitException


def _make_mock_redis(*, allowed: bool, retry_after: int = 0):
    script = AsyncMock(return_value=[1 if allowed else 0, retry_after])
    client = MagicMock()
    client.register_script = MagicMock(return_value=script)
    return client, script


@pytest.mark.asyncio
async def test_rate_limiter_allows_request_within_limit():
    client, _ = _make_mock_redis(allowed=True)
    limiter = RateLimiter(client)

    await limiter.check(
        endpoint_key="chat_message",
        org_id="org-1",
        user_id="user-1",
        limit=60,
        window_seconds=60,
    )


@pytest.mark.asyncio
async def test_rate_limiter_raises_on_exceeded_limit():
    client, _ = _make_mock_redis(allowed=False, retry_after=42)
    limiter = RateLimiter(client)

    with pytest.raises(RateLimitException) as exc_info:
        await limiter.check(
            endpoint_key="chat_message",
            org_id="org-1",
            user_id="user-1",
            limit=60,
            window_seconds=60,
        )

    assert exc_info.value.status_code == 429
    assert exc_info.value.retry_after == 42


@pytest.mark.asyncio
async def test_rate_limiter_isolates_different_orgs():
    call_keys: list[str] = []

    async def fake_script(keys, args):
        call_keys.append(keys[0])
        return [1, 0]

    script = fake_script
    client = MagicMock()
    client.register_script = MagicMock(return_value=script)
    limiter = RateLimiter(client)

    await limiter.check(endpoint_key="ep", org_id="org-a", user_id="u1", limit=10, window_seconds=60)
    await limiter.check(endpoint_key="ep", org_id="org-b", user_id="u1", limit=10, window_seconds=60)

    assert call_keys[0] != call_keys[1]
    assert "org-a" in call_keys[0]
    assert "org-b" in call_keys[1]


def test_rate_limit_exception_carries_retry_after():
    exc = RateLimitException(retry_after=30)
    assert exc.status_code == 429
    assert exc.retry_after == 30
    assert exc.error_code == "rate_limit_exceeded"
    assert exc.details["retry_after_seconds"] == 30


@pytest.mark.asyncio
async def test_rate_limiter_redis_not_initialized():
    from src.security.rateLimitDependency import _get_redis_client
    from src.shared.customExceptions import BaseApplicationException
    
    request = MagicMock()
    request.app.state.redis_client = None
    
    with pytest.raises(BaseApplicationException) as exc_info:
        _get_redis_client(request)
        
    assert exc_info.value.status_code == 503
    assert exc_info.value.error_code == "rate_limit_unavailable"


@pytest.mark.asyncio
async def test_rate_limiter_redis_connection_failure():
    from src.security.rateLimitDependency import rate_limited
    from src.shared.customExceptions import BaseApplicationException
    
    broken_client = MagicMock()
    script = AsyncMock(side_effect=Exception("Redis connection lost"))
    broken_client.register_script = MagicMock(return_value=script)
    
    request = MagicMock()
    request.app.state.redis_client = broken_client
    request.app.state.settings = MagicMock()
    request.app.state.settings.rate_limit_window_seconds = 60
    
    user = MagicMock()
    user.organization_id = "org-1"
    user.id = "user-1"
    
    dep = rate_limited("endpoint", lambda s: 60)
    
    with pytest.raises(BaseApplicationException) as exc_info:
        await dep(request=request, user=user, session=MagicMock())
        
    assert exc_info.value.status_code == 503
    assert exc_info.value.error_code == "rate_limit_unavailable"

