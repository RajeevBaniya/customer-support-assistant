from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.ingestionJobModel import (
    INGESTION_JOB_CANCELLED,
    INGESTION_JOB_COMPLETED,
    INGESTION_JOB_FAILED,
    INGESTION_JOB_PENDING,
    INGESTION_JOB_PROCESSING,
    IngestionJob,
)


class IngestionJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, row: IngestionJob) -> IngestionJob:
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_by_id_for_org(
        self,
        job_id: UUID,
        organization_id: UUID,
    ) -> IngestionJob | None:
        stmt = select(IngestionJob).where(
            IngestionJob.id == job_id,
            IngestionJob.organization_id == organization_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, job_id: UUID) -> IngestionJob | None:
        stmt = select(IngestionJob).where(IngestionJob.id == job_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def cancel_active_for_document(self, *, document_id: UUID) -> int:
        stmt = (
            update(IngestionJob)
            .where(
                IngestionJob.document_id == document_id,
                IngestionJob.status.in_((INGESTION_JOB_PENDING, INGESTION_JOB_PROCESSING)),
            )
            .values(
                status=INGESTION_JOB_CANCELLED,
                completed_at=datetime.now(UTC),
                error_message=None,
            )
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return int(result.rowcount or 0)

    async def claim_pending_or_resume_processing(
        self,
        *,
        job_id: UUID,
        allow_resume_processing: bool,
    ) -> IngestionJob | None:
        stmt = select(IngestionJob).where(IngestionJob.id == job_id).with_for_update()
        result = await self._session.execute(stmt)
        job = result.scalar_one_or_none()
        if job is None:
            return None
        if job.status in (INGESTION_JOB_COMPLETED, INGESTION_JOB_FAILED, INGESTION_JOB_CANCELLED):
            return None
        if job.status == INGESTION_JOB_PROCESSING:
            return job if allow_resume_processing else None
        if job.status == INGESTION_JOB_PENDING:
            job.status = INGESTION_JOB_PROCESSING
            if job.started_at is None:
                job.started_at = datetime.now(UTC)
            await self._session.flush()
            return job
        return None

    async def mark_completed(self, job_id: UUID) -> None:
        stmt = (
            update(IngestionJob)
            .where(
                IngestionJob.id == job_id,
                IngestionJob.status == INGESTION_JOB_PROCESSING,
            )
            .values(
                status=INGESTION_JOB_COMPLETED,
                completed_at=datetime.now(UTC),
                error_message=None,
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def mark_failed(self, job_id: UUID, *, message: str) -> None:
        stmt = (
            update(IngestionJob)
            .where(
                IngestionJob.id == job_id,
                IngestionJob.status.in_((INGESTION_JOB_PENDING, INGESTION_JOB_PROCESSING)),
            )
            .values(
                status=INGESTION_JOB_FAILED,
                completed_at=datetime.now(UTC),
                error_message=message[:8000],
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def increment_retry_count(self, job_id: UUID) -> None:
        job = await self.get_by_id(job_id)
        if job is None:
            return
        job.retry_count = int(job.retry_count) + 1
        await self._session.flush()
