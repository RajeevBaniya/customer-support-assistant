from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.observability.metrics.recorders import record_workflow_node
from src.observability.tracing.correlation import get_correlation_id, get_workflow_id


def enrich_trace_row(row: Mapping[str, Any], *, graph: str, node: str) -> dict[str, Any]:
    record_workflow_node(graph=graph, node=node, status="ok")
    out = dict(row)
    cid = get_correlation_id()
    if cid:
        out["correlation_id"] = cid
    wid = get_workflow_id()
    if wid:
        out["workflow_id"] = wid
    return out
