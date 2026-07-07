from typing import cast

from starlette.requests import Request

from src.observability.metrics.recorders import record_http_request
from src.observability.tracing.correlation import resolve_correlation_id


def test_record_http_request_does_not_raise() -> None:
    record_http_request(method="GET", route="/health", status_code=200, duration_s=0.01)


def test_correlation_precedence_request_id() -> None:
    class _Headers:
        def get(self, key: str) -> str | None:
            if key == "X-Request-ID":
                return "req-1"
            if key == "X-Correlation-ID":
                return "corr-2"
            return None

    class _Req:
        headers = _Headers()

    assert resolve_correlation_id(cast(Request, _Req())) == "req-1"
