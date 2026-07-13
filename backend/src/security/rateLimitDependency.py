from collections.abc import Callable, Coroutine
from typing import Any

import redis.asyncio as redis_async
from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.userAccess import get_application_user
from src.core.appEnvironment import AppEnvironment
from src.database.databaseSession import get_db_session
from src.models.userModel import User
from src.observability.structuredLogger import get_logger
from src.security.rateLimiter import RateLimiter
from src.shared.customExceptions import BaseApplicationException, RateLimitException
from src.shared.responseFormatter import format_error_response

logger = get_logger("security.rate_limit_dependency")


def _get_redis_client(request: Request) -> redis_async.Redis:
    client = getattr(request.app.state, "redis_client", None)
    if client is None:
        raise BaseApplicationException(
            "Rate limiting service is currently unavailable",
            error_code="rate_limit_unavailable",
            status_code=503,
            details={"reason": "redis_not_initialized"},
        )
    if not isinstance(client, redis_async.Redis):
        raise TypeError("redis_client must be redis_async.Redis")
    return client


def rate_limited(
    endpoint_key: str,
    limit_getter: Callable[[AppEnvironment], int],
) -> Callable[..., Coroutine[Any, Any, None]]:
    async def _dependency(
        request: Request,
        user: User = Depends(get_application_user),
        session: AsyncSession = Depends(get_db_session),
    ) -> None:
        settings: AppEnvironment = request.app.state.settings
        client = _get_redis_client(request)

        try:
            limiter = RateLimiter(client)
            await limiter.check(
                endpoint_key=endpoint_key,
                org_id=str(user.organization_id),
                user_id=str(user.id),
                limit=limit_getter(settings),
                window_seconds=settings.rate_limit_window_seconds,
            )
        except RateLimitException:
            raise
        except Exception as exc:
            logger.error("rate_limiter_redis_failure", error=str(exc))
            raise BaseApplicationException(
                "Rate limiting service is currently unavailable",
                error_code="rate_limit_unavailable",
                status_code=503,
                details={"reason": "redis_connection_error"},
            ) from exc

    return _dependency



def rate_limit_exception_response(exc: RateLimitException) -> JSONResponse:
    payload = format_error_response(
        code=exc.error_code,
        message=exc.message,
        details=exc.details,
    )
    return JSONResponse(
        status_code=429,
        content=payload,
        headers={"Retry-After": str(exc.retry_after)},
    )
