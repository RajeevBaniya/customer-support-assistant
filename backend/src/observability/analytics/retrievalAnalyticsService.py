from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.observability.analytics.analytics_time_window import clamp_analytics_hours
from src.observability.analytics.repositories.analyticsQueryRepository import (
    EvaluationAnalyticsRepository,
    since_from_hours,
)
from src.observability.metrics.org_window_store import list_org_events
from src.schemas.analyticsSchemas import RetrievalAnalyticsSummary


class RetrievalAnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self._eval = EvaluationAnalyticsRepository(session)

    async def summarize(self, *, organization_id: UUID, hours: int) -> RetrievalAnalyticsSummary:
        window = clamp_analytics_hours(hours)
        live = list_org_events(organization_id=organization_id, kind="retrieval", hours=window)
        chunks: list[int] = []
        sims: list[float] = []
        rerank_reduction: list[float] = []
        near_dup: list[int] = []
        sufficiency: list[float] = []
        for ev in live:
            p = ev.payload
            chunks.append(int(p.get("final_chunks") or 0))
            sims.append(float(p.get("avg_similarity") or 0.0))
            rerank_reduction.append(float(p.get("rerank_reduction_pct") or 0.0))
            near_dup.append(int(p.get("near_dup_dropped") or 0))
            sufficiency.append(float(p.get("sufficiency") or 0.0))

        since = since_from_hours(window)
        eval_rows = await self._eval.results_since(organization_id=organization_id, since=since)
        for row in eval_rows:
            refs = row.retrieved_chunk_refs
            if isinstance(refs, list):
                chunks.append(len(refs))

        n = max(1, len(chunks)) if chunks else 0
        return RetrievalAnalyticsSummary(
            hours=window,
            sample_count=len(chunks),
            avg_chunks=round(sum(chunks) / n, 3) if chunks else 0.0,
            avg_similarity=round(sum(sims) / max(1, len(sims)), 4) if sims else 0.0,
            avg_rerank_reduction_pct=(
                round(sum(rerank_reduction) / max(1, len(rerank_reduction)), 2)
                if rerank_reduction
                else 0.0
            ),
            total_near_dup_dropped=sum(near_dup),
            avg_sufficiency=(
                round(sum(sufficiency) / max(1, len(sufficiency)), 4) if sufficiency else 0.0
            ),
        )
