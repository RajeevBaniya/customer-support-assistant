from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.appEnvironment import AppEnvironment
from src.documents.documentRepository import DocumentRepository
from src.documents.ingestionJobRepository import IngestionJobRepository
from src.documents.ingestionRetryPolicy import (
    IngestionTransientError,
    is_transient_ingestion_failure,
)
from src.documents.ingestVectors import run_embedding_ingest
from src.documents.postUploadParse import run_parse_and_preview
from src.models.ingestionJobModel import INGESTION_JOB_CANCELLED
from src.storage.storageBinding import storage_provider_for


async def _job_is_cancelled(session: AsyncSession, job_id: UUID) -> bool:
    repo = IngestionJobRepository(session)
    row = await repo.get_by_id(job_id)
    return row is not None and row.status == INGESTION_JOB_CANCELLED


async def run_ingestion_for_job(
    *,
    session: AsyncSession,
    settings: AppEnvironment,
    job_id: UUID,
    celery_retries: int,
) -> None:
    jobs = IngestionJobRepository(session)
    docs = DocumentRepository(session)
    allow_resume = celery_retries > 0
    job = await jobs.claim_pending_or_resume_processing(
        job_id=job_id,
        allow_resume_processing=allow_resume,
    )
    if job is None:
        return
    document = await docs.get_by_id_for_org(job.document_id, job.organization_id)
    if document is None:
        await jobs.mark_failed(job_id, message="document_missing")
        await session.commit()
        return
    if document.upload_status != "stored":
        await jobs.mark_failed(job_id, message="upload_not_stored")
        await session.commit()
        return
    if await _job_is_cancelled(session, job_id):
        await session.commit()
        return
    storage = storage_provider_for(settings)
    try:
        data = await storage.get_file(
            organization_id=document.organization_id,
            storage_path=document.storage_path,
        )
    except Exception as exc:
        if is_transient_ingestion_failure(exc):
            raise IngestionTransientError(str(exc)) from exc
        await jobs.mark_failed(job_id, message=f"storage_read:{exc!s}")
        await session.commit()
        return
    if await _job_is_cancelled(session, job_id):
        await session.commit()
        return
    parsed = await run_parse_and_preview(
        document_id=document.id,
        mime_type=document.mime_type,
        data=data,
        settings=settings,
    )
    document.parsing_status = parsed.parsing_status
    document.parser_type = parsed.parser_type
    document.chunk_count = parsed.chunk_count
    document.parsed_at = parsed.parsed_at
    if parsed.parsing_status != "parsed":
        document.embedding_status = "skipped"
    await docs.flush()
    await session.commit()
    if await _job_is_cancelled(session, job_id):
        return
    if parsed.parsing_status != "parsed":
        await jobs.mark_failed(
            job_id,
            message=parsed.parse_error or "parse_failed",
        )
        await session.commit()
        return
    try:
        await run_embedding_ingest(
            session=session,
            settings=settings,
            row=document,
            parsed=parsed,
            raise_transient=True,
        )
    except IngestionTransientError:
        raise
    except Exception as exc:
        await jobs.mark_failed(job_id, message=f"embed:{exc!s}")
        await session.commit()
        return
    await docs.flush()
    if document.embedding_status == "failed":
        await jobs.mark_failed(job_id, message="embedding_failed")
        await session.commit()
        return
    if await _job_is_cancelled(session, job_id):
        return
    await jobs.mark_completed(job_id)
    await session.commit()
