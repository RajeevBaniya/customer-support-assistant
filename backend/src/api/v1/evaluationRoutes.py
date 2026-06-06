from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.userAccess import get_application_user
from src.core.appEnvironment import AppEnvironment
from src.database.databaseSession import get_db_session
from src.evaluation.benchmarkDatasetService import BenchmarkDatasetService
from src.evaluation.evaluationReadService import EvaluationReadService
from src.evaluation.evaluationRunService import EvaluationRunService
from src.models.userModel import User
from src.schemas.evaluationSchemas import (
    BenchmarkDatasetCreate,
    BenchmarkDatasetResponse,
    EvaluationRunQueuedResponse,
    EvaluationRunRequest,
)
from src.security.rateLimitDependency import rate_limited
from src.shared.responseFormatter import format_success_response

evaluation_router = APIRouter(prefix="/evaluation", tags=["evaluation"])

_rate_limit_run = rate_limited("evaluation_run", lambda s: s.rate_limit_evaluation_run)
_rate_limit_benchmark_run = rate_limited("benchmark_run", lambda s: s.rate_limit_benchmark_run)


@evaluation_router.post("/run", dependencies=[Depends(_rate_limit_run)])
async def post_evaluation_run(
    request: Request,
    body: EvaluationRunRequest,
    user: User = Depends(get_application_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    settings: AppEnvironment = request.app.state.settings
    svc = EvaluationRunService.from_request(session, settings)
    run_id = await svc.run_single_sync(user=user, req=body)
    payload = EvaluationRunQueuedResponse(run_id=run_id, status="completed").model_dump(mode="json")
    out = format_success_response(payload, message="Evaluation")
    return JSONResponse(content=out)


@evaluation_router.get("/runs")
async def list_evaluation_runs(
    request: Request,
    user: User = Depends(get_application_user),
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Response:
    settings: AppEnvironment = request.app.state.settings
    svc = EvaluationReadService.from_request(session, settings)
    rows = await svc.list_runs(user=user, limit=limit, offset=offset)
    out = format_success_response(
        {"items": [r.model_dump(mode="json") for r in rows]},
        message="Evaluation",
    )
    return JSONResponse(content=out)


@evaluation_router.get("/runs/{run_id}")
async def get_evaluation_run(
    request: Request,
    run_id: UUID,
    user: User = Depends(get_application_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    settings: AppEnvironment = request.app.state.settings
    svc = EvaluationReadService.from_request(session, settings)
    detail = await svc.get_run_detail(user=user, run_id=run_id)
    out = format_success_response(detail.model_dump(mode="json"), message="Evaluation")
    return JSONResponse(content=out)


@evaluation_router.post("/benchmark/{dataset_id}/run", dependencies=[Depends(_rate_limit_benchmark_run)])
async def post_benchmark_run(
    request: Request,
    dataset_id: UUID,
    user: User = Depends(get_application_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    settings: AppEnvironment = request.app.state.settings
    svc = EvaluationRunService.from_request(session, settings)
    run_id = await svc.start_benchmark_run(user=user, dataset_id=dataset_id)
    payload = EvaluationRunQueuedResponse(run_id=run_id, status="queued").model_dump(mode="json")
    out = format_success_response(payload, message="Evaluation")
    return JSONResponse(content=out)


@evaluation_router.post("/benchmarks")
async def post_benchmark_dataset(
    request: Request,
    body: BenchmarkDatasetCreate,
    user: User = Depends(get_application_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    settings: AppEnvironment = request.app.state.settings
    svc = BenchmarkDatasetService.from_request(session, settings)
    ds = await svc.create(user=user, payload=body)
    row_count = len(ds.rows) if isinstance(ds.rows, list) else 0
    payload = BenchmarkDatasetResponse(id=ds.id, name=ds.name, row_count=row_count)
    out = format_success_response(payload.model_dump(mode="json"), message="Evaluation")
    return JSONResponse(content=out)


@evaluation_router.get("/benchmarks")
async def list_benchmark_datasets(
    request: Request,
    user: User = Depends(get_application_user),
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Response:
    settings: AppEnvironment = request.app.state.settings
    svc = BenchmarkDatasetService.from_request(session, settings)
    rows = await svc.list_for_user(user=user, limit=limit, offset=offset)
    items = []
    for r in rows:
        rc = len(r.rows) if isinstance(r.rows, list) else 0
        payload = BenchmarkDatasetResponse(
            id=r.id,
            name=r.name,
            row_count=rc,
        ).model_dump(mode="json")
        items.append(payload)
    out = format_success_response({"items": items}, message="Evaluation")
    return JSONResponse(content=out)
