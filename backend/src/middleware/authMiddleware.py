import json
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.auth.clerkAuth import verify_bearer_token
from src.core.appEnvironment import AppEnvironment
from src.observability.structuredLogger import get_logger
from src.shared.customExceptions import AuthException
from src.shared.responseFormatter import format_error_response

logger = get_logger("middleware.auth")


def _is_public_path(path: str) -> bool:
    if path in {"/live", "/ready", "/health"}:
        return True
    if path.startswith("/docs") or path.startswith("/redoc") or path == "/openapi.json":
        return True
    return False


def _requires_bearer(path: str, api_prefix: str) -> bool:
    if not path.startswith(api_prefix):
        return False
    return (
        path.startswith(f"{api_prefix}/auth/")
        or path.startswith(f"{api_prefix}/users/")
        or path.startswith(f"{api_prefix}/documents")
        or path.startswith(f"{api_prefix}/chat/")
    )


def _json_response(status: int, body: dict[str, object]) -> Response:
    return Response(
        status_code=status,
        media_type="application/json",
        content=json.dumps(body).encode("utf-8"),
    )


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        path = request.url.path
        if _is_public_path(path):
            return await call_next(request)

        settings: AppEnvironment = request.app.state.settings
        if not _requires_bearer(path, settings.api_prefix):
            return await call_next(request)

        header = request.headers.get("authorization") or request.headers.get("Authorization")
        if not header or not header.lower().startswith("bearer "):
            payload = format_error_response(
                code="auth_error",
                message="Bearer token required",
                details={"path": path},
            )
            return _json_response(401, payload)

        raw = header.split(" ", 1)[1].strip()
        try:
            token = await verify_bearer_token(raw, settings)
        except AuthException as exc:
            logger.warning("auth_token_rejected", path=path, error=exc.message)
            payload = format_error_response(
                code=exc.error_code,
                message=exc.message,
                details=exc.details,
            )
            return _json_response(401, payload)

        request.state.clerk_token = token
        return await call_next(request)
