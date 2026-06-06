from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

_ALWAYS_ON_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
}

_HSTS_HEADER = "Strict-Transport-Security"
_HSTS_VALUE = "max-age=63072000; includeSubDomains"
_STRICT_ENVS = frozenset({"production", "staging"})


class SecureHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        try:
            response = await call_next(request)
        except Exception:
            from fastapi.responses import PlainTextResponse

            response = PlainTextResponse("Internal Server Error", status_code=500)

        for name, value in _ALWAYS_ON_HEADERS.items():
            if name != "Content-Security-Policy":
                response.headers[name] = value

        path = request.url.path
        if path in {"/docs", "/redoc", "/openapi.json"} or path.startswith(("/docs/", "/redoc/")):
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https://cdn.jsdelivr.net; "
                "frame-ancestors 'none'"
            )
        else:
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; frame-ancestors 'none'"
            )

        settings = getattr(request.app.state, "settings", None)
        if settings is not None:
            env = str(getattr(settings, "app_env", "")).strip().lower()
            if env in _STRICT_ENVS:
                response.headers[_HSTS_HEADER] = _HSTS_VALUE

        return response
