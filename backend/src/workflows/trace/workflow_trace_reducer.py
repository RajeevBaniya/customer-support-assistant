from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

MAX_TRACE_ENTRIES = 64
MAX_TRACE_CHARS = 8000


def _entry_chars(entry: Mapping[str, Any]) -> int:
    return len(json.dumps(entry, default=str, separators=(",", ":")))


def _trim_trace(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    trimmed = entries[-MAX_TRACE_ENTRIES:]
    while trimmed and sum(_entry_chars(e) for e in trimmed) > MAX_TRACE_CHARS:
        trimmed = trimmed[1:]
    return trimmed


def workflow_trace_reducer(
    left: Sequence[Mapping[str, Any]] | None,
    right: Sequence[Mapping[str, Any]] | None,
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = [dict(x) for x in (left or ())]
    for row in right or ():
        merged.append(dict(row))
    return _trim_trace(merged)
