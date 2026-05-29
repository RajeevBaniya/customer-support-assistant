from __future__ import annotations

from contextvars import ContextVar
from uuid import uuid4

from starlette.requests import Request

CORRELATION_HEADER_REQUEST = "X-Request-ID"
CORRELATION_HEADER_ALT = "X-Correlation-ID"
RESPONSE_CORRELATION_HEADER = "X-Request-ID"

_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_workflow_id: ContextVar[str | None] = ContextVar("workflow_id", default=None)


def resolve_correlation_id(request: Request) -> str:
    for header in (CORRELATION_HEADER_REQUEST, CORRELATION_HEADER_ALT):
        raw = request.headers.get(header)
        if raw and str(raw).strip():
            return str(raw).strip()[:128]
    return str(uuid4())


def set_correlation_id(value: str) -> None:
    _correlation_id.set(value)


def get_correlation_id() -> str | None:
    return _correlation_id.get()


def clear_tracing_context() -> None:
    _correlation_id.set(None)
    _workflow_id.set(None)


def start_workflow_trace() -> str:
    wid = str(uuid4())
    _workflow_id.set(wid)
    return wid


def get_workflow_id() -> str | None:
    return _workflow_id.get()
