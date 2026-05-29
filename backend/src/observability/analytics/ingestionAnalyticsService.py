from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.observability.analytics.analytics_time_window import clamp_analytics_hours
from src.observability.analytics.repositories.analyticsQueryRepository import (
    IngestionAnalyticsRepository,
    since_from_hours,
)
from src.schemas.analyticsSchemas import IngestionAnalyticsSummary


class IngestionAnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = IngestionAnalyticsRepository(session)

    async def summarize(self, *, organization_id: UUID, hours: int) -> IngestionAnalyticsSummary:
        window = clamp_analytics_hours(hours)
        since = since_from_hours(window)
        jobs = await self._repo.jobs_since(organization_id=organization_id, since=since)
        status_counts = await self._repo.count_by_status(
            organization_id=organization_id,
            since=since,
        )
        durations: list[float] = []
        for job in jobs:
            if job.started_at is None or job.completed_at is None:
                continue
            delta = (job.completed_at - job.started_at).total_seconds()
            if delta >= 0:
                durations.append(delta)
        avg_duration = round(sum(durations) / len(durations), 3) if durations else 0.0
        return IngestionAnalyticsSummary(
            hours=window,
            job_count=len(jobs),
            status_counts=status_counts,
            avg_duration_seconds=avg_duration,
        )
