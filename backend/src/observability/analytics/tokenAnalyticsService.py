from __future__ import annotations

from uuid import UUID

from src.observability.analytics.analytics_time_window import clamp_analytics_hours
from src.observability.metrics.org_window_store import list_org_events
from src.schemas.analyticsSchemas import TokenAnalyticsSummary


class TokenAnalyticsService:
    def summarize(self, *, organization_id: UUID, hours: int) -> TokenAnalyticsSummary:
        window = clamp_analytics_hours(hours)
        events = list_org_events(organization_id=organization_id, kind="token", hours=window)
        by_provider: dict[str, dict[str, int]] = {}
        by_route: dict[str, dict[str, int]] = {}
        estimated_rows = 0
        for ev in events:
            p = ev.payload
            provider = str(p.get("provider") or "unknown")
            route = str(p.get("route_type") or "unknown")
            prompt = int(p.get("prompt_tokens") or 0)
            completion = int(p.get("completion_tokens") or 0)
            total = int(p.get("total_tokens") or 0)
            if bool(p.get("estimated")):
                estimated_rows += 1
            prov = by_provider.setdefault(
                provider,
                {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            )
            prov["prompt_tokens"] += prompt
            prov["completion_tokens"] += completion
            prov["total_tokens"] += total
            rt = by_route.setdefault(
                route,
                {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            )
            rt["prompt_tokens"] += prompt
            rt["completion_tokens"] += completion
            rt["total_tokens"] += total
        grand = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        for row in by_provider.values():
            grand["prompt_tokens"] += row["prompt_tokens"]
            grand["completion_tokens"] += row["completion_tokens"]
            grand["total_tokens"] += row["total_tokens"]
        return TokenAnalyticsSummary(
            hours=window,
            totals=grand,
            by_provider=by_provider,
            by_route=by_route,
            estimated_event_count=estimated_rows,
        )
