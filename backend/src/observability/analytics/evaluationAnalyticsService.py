from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.evaluation.evaluationConstants import evaluation_result_passes
from src.observability.analytics.analytics_time_window import clamp_analytics_hours
from src.observability.analytics.repositories.analyticsQueryRepository import (
    EvaluationAnalyticsRepository,
    since_from_hours,
)
from src.schemas.analyticsSchemas import EvaluationAnalyticsSummary


class EvaluationAnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = EvaluationAnalyticsRepository(session)

    async def summarize(self, *, organization_id: UUID, hours: int) -> EvaluationAnalyticsSummary:
        window = clamp_analytics_hours(hours)
        since = since_from_hours(window)
        rows = await self._repo.results_since(organization_id=organization_id, since=since)
        if not rows:
            return EvaluationAnalyticsSummary(
                hours=window,
                result_count=0,
                pass_count=0,
                fail_count=0,
                avg_faithfulness=0.0,
                avg_hallucination=0.0,
                avg_retrieval_relevance=0.0,
            )
        pass_count = 0
        fail_count = 0
        faith = 0.0
        hall = 0.0
        retr = 0.0
        for r in rows:
            ok = evaluation_result_passes(
                hallucination_score=r.hallucination_score,
                faithfulness_score=r.faithfulness_score,
            )
            if ok:
                pass_count += 1
            else:
                fail_count += 1
            faith += r.faithfulness_score
            hall += r.hallucination_score
            retr += r.retrieval_relevance_score
        n = len(rows)
        return EvaluationAnalyticsSummary(
            hours=window,
            result_count=n,
            pass_count=pass_count,
            fail_count=fail_count,
            avg_faithfulness=round(faith / n, 4),
            avg_hallucination=round(hall / n, 4),
            avg_retrieval_relevance=round(retr / n, 4),
        )
