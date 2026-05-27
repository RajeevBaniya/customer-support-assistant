from typing import Any

from src.core.appEnvironment import AppEnvironment
from src.jobs.jobConfig import celery_broker_url


def celery_configured(settings: AppEnvironment) -> bool:
    return celery_broker_url(settings) is not None


def celery_worker_ping_sync() -> bool:
    try:
        from src.jobs.celeryApp import celery_app

        inspector = celery_app.control.inspect(timeout=0.8)
        if inspector is None:
            return False
        pong = inspector.ping()
        return bool(pong)
    except Exception:
        return False


def celery_health_bundle(
    settings: AppEnvironment,
    *,
    redis_reachable: bool,
) -> dict[str, Any]:
    broker_ok = bool(redis_reachable and celery_configured(settings))
    worker_ok = False
    if broker_ok:
        worker_ok = celery_worker_ping_sync()
    return {
        "celery_configured": celery_configured(settings),
        "celery_broker_ok": broker_ok,
        "celery_worker_ping": worker_ok,
        "ingestion_pipeline_ready": broker_ok and worker_ok,
    }
