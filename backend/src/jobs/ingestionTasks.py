from __future__ import annotations

import asyncio
from uuid import UUID

from celery import Task

from src.core.appEnvironment import get_app_environment
from src.database.databaseSession import session_scope
from src.documents.ingestionJobRepository import IngestionJobRepository
from src.documents.ingestionRetryPolicy import backoff_seconds, is_transient_ingestion_failure
from src.jobs.celeryApp import celery_app
from src.jobs.ingestionOrchestrator import run_ingestion_for_job
from src.observability.structuredLogger import get_logger

logger = get_logger(__name__)


async def _increment_job_retry(job_id: UUID) -> None:
    async with session_scope() as session:
        repo = IngestionJobRepository(session)
        await repo.increment_retry_count(job_id)


async def _fail_job_unhandled(job_id: UUID, message: str) -> None:
    async with session_scope() as session:
        repo = IngestionJobRepository(session)
        await repo.mark_failed(job_id, message=message[:8000])


@celery_app.task(bind=True, name="recallstack.ingestion.run")  # type: ignore[misc]
def run_ingestion_task(self: Task, job_id: str) -> None:
    settings = get_app_environment()
    retries = int(getattr(self.request, "retries", 0) or 0)
    max_retries = int(settings.ingestion_max_retries)
    jid = UUID(job_id)

    async def _run() -> None:
        async with session_scope() as session:
            await run_ingestion_for_job(
                session=session,
                settings=settings,
                job_id=jid,
                celery_retries=retries,
            )

    try:
        asyncio.run(_run())
    except Exception as exc:
        if is_transient_ingestion_failure(exc) and retries < max_retries:
            asyncio.run(_increment_job_retry(jid))
            countdown = backoff_seconds(
                attempt=retries + 1,
                base=settings.ingestion_retry_backoff_seconds,
            )
            logger.info(
                "ingestion_task_retry",
                job_id=job_id,
                countdown=countdown,
                attempt=retries + 1,
            )
            raise self.retry(exc=exc, countdown=countdown) from exc
        logger.warning("ingestion_task_failed", job_id=job_id, exc_type=type(exc).__name__)
        asyncio.run(_fail_job_unhandled(jid, str(exc)))
        raise


def enqueue_ingestion_job(*, job_id: UUID) -> None:
    run_ingestion_task.delay(str(job_id))
