from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any
from uuid import UUID

MAX_ORG_EVENTS = 20000
MAX_EVENT_AGE_SECONDS = 168 * 3600


@dataclass(frozen=True)
class OrgWindowEvent:
    ts: float
    organization_id: str
    kind: str
    payload: dict[str, Any]


_lock = threading.Lock()
_events: list[OrgWindowEvent] = []


def append_org_event(
    *,
    organization_id: UUID,
    kind: str,
    payload: dict[str, Any],
) -> None:
    now = time.time()
    row = OrgWindowEvent(
        ts=now,
        organization_id=str(organization_id),
        kind=kind,
        payload=payload,
    )
    with _lock:
        _events.append(row)
        cutoff = now - MAX_EVENT_AGE_SECONDS
        while _events and (_events[0].ts < cutoff or len(_events) > MAX_ORG_EVENTS):
            _events.pop(0)


def list_org_events(
    *,
    organization_id: UUID,
    kind: str,
    hours: int,
) -> list[OrgWindowEvent]:
    now = time.time()
    floor = now - (hours * 3600)
    oid = str(organization_id)
    with _lock:
        return [e for e in _events if e.organization_id == oid and e.kind == kind and e.ts >= floor]
