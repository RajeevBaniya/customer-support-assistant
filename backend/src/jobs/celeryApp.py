from __future__ import annotations

import asyncio
from typing import Any

from celery import Celery, signals

from src.core.appEnvironment import get_app_environment
from src.database.databaseManager import DatabaseManager
from src.database.databaseSession import clear_session_factory, configure_session_factory
from src.jobs.jobConfig import build_celery_conf
from src.observability.structuredLogger import get_logger

logger = get_logger(__name__)

_worker_db: DatabaseManager | None = None


def create_celery_app() -> Celery:
    settings = get_app_environment()
    conf = build_celery_conf(settings)
    filtered: dict[str, Any] = {k: v for k, v in conf.items() if v is not None}
    app = Celery("recallstack")
    app.conf.update(filtered)
    return app


celery_app = create_celery_app()


@signals.worker_process_init.connect  # type: ignore[misc]
def _worker_process_init(**_kwargs: Any) -> None:
    global _worker_db
    settings = get_app_environment()
    _worker_db = DatabaseManager(settings)
    configure_session_factory(_worker_db.engine)
    logger.info("celery_worker_db_ready")


@signals.worker_process_shutdown.connect  # type: ignore[misc]
def _worker_process_shutdown(**_kwargs: Any) -> None:
    global _worker_db
    if _worker_db is not None:
        asyncio.run(_worker_db.close())
    clear_session_factory()
    _worker_db = None
    logger.info("celery_worker_db_closed")


def _load_task_modules() -> tuple[object, object]:
    from src.jobs import evaluationTasks, ingestionTasks

    return evaluationTasks, ingestionTasks


_ = _load_task_modules()
