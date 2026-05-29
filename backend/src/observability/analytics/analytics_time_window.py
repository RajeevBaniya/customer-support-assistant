from __future__ import annotations

MAX_ANALYTICS_HOURS = 168
DEFAULT_ANALYTICS_HOURS = 24


def clamp_analytics_hours(raw: int) -> int:
    if raw < 1:
        return DEFAULT_ANALYTICS_HOURS
    if raw > MAX_ANALYTICS_HOURS:
        raise ValueError("analytics_hours_over_limit")
    return raw
