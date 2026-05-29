from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.observability.metrics.recorders import record_http_request
from src.observability.structuredLogger import bind_request_context, clear_request_context
from src.observability.tracing.correlation import (
    RESPONSE_CORRELATION_HEADER,
    clear_tracing_context,
    resolve_correlation_id,
    set_correlation_id,
)


def _route_template(path: str, api_prefix: str) -> str:
    if path.startswith(api_prefix):
        rest = path[len(api_prefix) :]
        parts = [p for p in rest.split("/") if p]
        if not parts:
            return f"{api_prefix}/"
        head = parts[0]
        if len(parts) >= 2 and parts[1] not in {"run", "runs", "stream", "message", "ask"}:
            return f"{api_prefix}/{head}/{{id}}"
        if len(parts) >= 2:
            return f"{api_prefix}/{head}/{parts[1]}"
        return f"{api_prefix}/{head}"
    return path


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        correlation_id = resolve_correlation_id(request)
        set_correlation_id(correlation_id)
        request.state.correlation_id = correlation_id

        settings = request.app.state.settings
        route = _route_template(request.url.path, settings.api_prefix)
        method = request.method.upper()
        t0 = time.perf_counter()
        status_code = 500

        bind_request_context(
            correlation_id=correlation_id,
            http_method=method,
            http_route=route,
        )

        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers[RESPONSE_CORRELATION_HEADER] = correlation_id
            return response
        except Exception:
            status_code = 500
            raise
        finally:
            duration_s = time.perf_counter() - t0
            record_http_request(
                method=method,
                route=route,
                status_code=status_code,
                duration_s=duration_s,
            )
            clear_request_context()
            clear_tracing_context()
