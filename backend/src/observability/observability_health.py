from __future__ import annotations

from typing import TypedDict

from prometheus_client import generate_latest

from src.observability.metrics import registry as _registry
from src.observability.tracing.correlation import get_correlation_id


class ObservabilityHealthBundle(TypedDict, total=False):
    metrics_ready: bool
    tracing_ready: bool
    observability_ready: bool
    metrics_error: str


def observability_health_bundle() -> ObservabilityHealthBundle:
    out: ObservabilityHealthBundle = {
        "metrics_ready": False,
        "tracing_ready": False,
        "observability_ready": False,
    }
    try:
        payload = generate_latest()
        if payload:
            out["metrics_ready"] = True
        _ = _registry.HTTP_REQUESTS
    except Exception as exc:
        out["metrics_error"] = str(exc)
    try:
        get_correlation_id()
        out["tracing_ready"] = True
    except Exception:
        out["tracing_ready"] = False
    out["observability_ready"] = bool(out.get("metrics_ready")) and bool(out.get("tracing_ready"))
    return out
