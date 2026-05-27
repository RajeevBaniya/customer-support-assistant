from datetime import UTC, datetime
from typing import Any, cast

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from src.ai.ragHealth import rag_health
from src.database.db_readiness import db_section, is_db_ready
from src.observability.celeryHealth import celery_health_bundle
from src.observability.evaluation_health import evaluation_health_bundle
from src.observability.redisHealth import redis_health
from src.observability.structuredLogger import get_logger
from src.observability.workflow_health import workflow_health_bundle
from src.parsing.parserRegistry import parsing_health
from src.retrieval.retrievalHealth import retrieval_health
from src.shared.responseFormatter import format_error_response, format_success_response
from src.storage.storageBinding import storage_health
from src.vectorstore.vectorHealth import vector_health

health_router = APIRouter(tags=["health"])
logger = get_logger(__name__)


async def _db_bundle_and_ready(request: Request) -> tuple[dict[str, Any], bool]:
    bundle = await db_section(request)
    return bundle, is_db_ready(bundle)


def _get_started_at(request: Request) -> datetime:
    return cast(datetime, request.app.state.started_at)


def _uptime_seconds(started_at: datetime) -> float:
    elapsed = datetime.now(UTC) - started_at
    return round(elapsed.total_seconds(), 3)


def _probe_success(
    *,
    probe: str,
    status: str,
    message: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    data = {"probe": probe, "status": status, **payload}
    return format_success_response(data, message=message)


def _probe_error(
    *,
    probe: str,
    status: str,
    code: str,
    message: str,
    details: dict[str, Any],
) -> dict[str, Any]:
    return format_error_response(
        code=code,
        message=message,
        details={"probe": probe, "status": status, **details},
    )


@health_router.get("/live")
async def live_probe(request: Request) -> JSONResponse:
    started_at = _get_started_at(request)
    payload = _probe_success(
        probe="live",
        status="alive",
        message="Process is running",
        payload={"uptime_seconds": _uptime_seconds(started_at)},
    )
    logger.info("live_probe_success")
    return JSONResponse(status_code=status.HTTP_200_OK, content=payload)


@health_router.get("/ready")
async def ready_probe(request: Request) -> JSONResponse:
    bundle, ready = await _db_bundle_and_ready(request)

    if ready:
        payload = _probe_success(
            probe="ready",
            status="ready",
            message="Application is ready to receive traffic",
            payload={"database": bundle},
        )
        logger.info("ready_probe_success", database_status=bundle["status"])
        return JSONResponse(status_code=status.HTTP_200_OK, content=payload)

    payload = _probe_error(
        probe="ready",
        status="not_ready",
        code="service_not_ready",
        message="Application dependencies are not ready",
        details={"database": bundle},
    )
    logger.warning("ready_probe_failed", database_bundle=bundle)
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=payload)


@health_router.get("/health")
async def health_probe(request: Request) -> JSONResponse:
    started_at = _get_started_at(request)
    settings = request.app.state.settings
    bundle, healthy = await _db_bundle_and_ready(request)
    application_status = "up" if healthy else "degraded"
    health_status = "healthy" if healthy else "unhealthy"

    issuer_ready = bool(settings.clerk_jwt_issuer and str(settings.clerk_jwt_issuer).strip())
    storage_bundle = await storage_health(settings)
    redis_bundle = await redis_health(settings)
    parsing_bundle = parsing_health()
    vector_bundle = await vector_health(settings)
    retrieval_bundle = await retrieval_health(settings)
    rag_bundle = await rag_health(settings)
    workflow_bundle = workflow_health_bundle()
    evaluation_bundle = evaluation_health_bundle()
    streaming_ready = bool(
        redis_bundle.get("redis_configured") and redis_bundle.get("redis_reachable")
    )
    redis_ok = bool(redis_bundle.get("redis_reachable"))
    celery_bundle = celery_health_bundle(settings, redis_reachable=redis_ok)
    health_data: dict[str, Any] = {
        "application": {
            "name": settings.app_name,
            "status": application_status,
        },
        "database": bundle,
        "auth": {
            "clerk_jwt_issuer_configured": issuer_ready,
            "jwt_validation_ready": issuer_ready or bool(settings.test_jwt_secret),
            "test_signing_enabled": bool(settings.test_jwt_secret),
        },
        "storage": storage_bundle,
        "redis": redis_bundle,
        "streaming_ready": streaming_ready,
        "celery": celery_bundle,
        "parsing": parsing_bundle,
        "vector": vector_bundle,
        "retrieval": retrieval_bundle,
        "rag": rag_bundle,
        "workflow": workflow_bundle,
        "evaluation": evaluation_bundle,
        "environment": settings.app_env,
        "metadata": {
            "api_prefix": settings.api_prefix,
            "debug": settings.debug,
            "uptime_seconds": _uptime_seconds(started_at),
            "checked_at": datetime.now(UTC).isoformat(),
        },
    }

    if healthy:
        payload = _probe_success(
            probe="health",
            status=health_status,
            message="Infrastructure health check passed",
            payload=health_data,
        )
        logger.info("health_probe_success", health_status=health_status)
        return JSONResponse(status_code=status.HTTP_200_OK, content=payload)

    payload = _probe_error(
        probe="health",
        status=health_status,
        code="infrastructure_unhealthy",
        message="Infrastructure health check failed",
        details=health_data,
    )
    logger.warning("health_probe_failed", health_status=health_status)
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=payload)
