from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.userAccess import get_application_user
from src.database.databaseSession import get_db_session
from src.models.userModel import User
from src.observability.analytics.analytics_time_window import MAX_ANALYTICS_HOURS
from src.observability.analytics.evaluationAnalyticsService import EvaluationAnalyticsService
from src.observability.analytics.ingestionAnalyticsService import IngestionAnalyticsService
from src.observability.analytics.retrievalAnalyticsService import RetrievalAnalyticsService
from src.observability.analytics.tokenAnalyticsService import TokenAnalyticsService
from src.shared.responseFormatter import format_success_response

analytics_router = APIRouter(prefix="/analytics", tags=["analytics"])


def _hours_query(hours: int = Query(default=24, ge=1, le=MAX_ANALYTICS_HOURS)) -> int:
    return hours


@analytics_router.get("/tokens")
async def analytics_tokens(
    request: Request,
    user: User = Depends(get_application_user),
    hours: int = Depends(_hours_query),
) -> Response:
    del request
    svc = TokenAnalyticsService()
    summary = svc.summarize(organization_id=user.organization_id, hours=hours)
    out = format_success_response(summary.model_dump(mode="json"), message="Analytics")
    return JSONResponse(content=out)


@analytics_router.get("/retrieval")
async def analytics_retrieval(
    request: Request,
    user: User = Depends(get_application_user),
    session: AsyncSession = Depends(get_db_session),
    hours: int = Depends(_hours_query),
) -> Response:
    del request
    svc = RetrievalAnalyticsService(session)
    summary = await svc.summarize(organization_id=user.organization_id, hours=hours)
    out = format_success_response(summary.model_dump(mode="json"), message="Analytics")
    return JSONResponse(content=out)


@analytics_router.get("/evaluations")
async def analytics_evaluations(
    request: Request,
    user: User = Depends(get_application_user),
    session: AsyncSession = Depends(get_db_session),
    hours: int = Depends(_hours_query),
) -> Response:
    del request
    svc = EvaluationAnalyticsService(session)
    summary = await svc.summarize(organization_id=user.organization_id, hours=hours)
    out = format_success_response(summary.model_dump(mode="json"), message="Analytics")
    return JSONResponse(content=out)


@analytics_router.get("/ingestion")
async def analytics_ingestion(
    request: Request,
    user: User = Depends(get_application_user),
    session: AsyncSession = Depends(get_db_session),
    hours: int = Depends(_hours_query),
) -> Response:
    del request
    svc = IngestionAnalyticsService(session)
    summary = await svc.summarize(organization_id=user.organization_id, hours=hours)
    out = format_success_response(summary.model_dump(mode="json"), message="Analytics")
    return JSONResponse(content=out)
