import json
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.appEnvironment import AppEnvironment
from src.observability.structuredLogger import get_logger
from src.shared.responseFormatter import format_error_response

logger = get_logger("middleware.organization")


def _json_response(status: int, body: dict[str, object]) -> Response:
    return Response(
        status_code=status,
        media_type="application/json",
        content=json.dumps(body).encode("utf-8"),
    )


class OrganizationMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        settings: AppEnvironment = request.app.state.settings
        path = request.url.path
        prefix_users = f"{settings.api_prefix}/users"
        prefix_documents = f"{settings.api_prefix}/documents"
        if path.startswith(prefix_users) or path.startswith(prefix_documents):
            token = getattr(request.state, "clerk_token", None)
            if token is None:
                logger.warning("organization_route_without_auth", path=path)
                payload = format_error_response(
                    code="auth_error",
                    message="Authentication required for organization routes",
                    details={"path": path},
                )
                return _json_response(401, payload)
        return await call_next(request)
