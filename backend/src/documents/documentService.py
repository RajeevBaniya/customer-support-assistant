from __future__ import annotations

from typing import Self
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.appEnvironment import AppEnvironment
from src.documents import mimeValidator, uploadSecurity
from src.documents.documentRepository import DocumentRepository
from src.documents.ingestionJobRepository import IngestionJobRepository
from src.jobs.ingestionTasks import enqueue_ingestion_job
from src.models.documentModel import Document
from src.models.ingestionJobModel import INGESTION_JOB_PENDING, IngestionJob
from src.models.userModel import User
from src.schemas.documentSchemas import (
    CancelIngestionResponse,
    DocumentListResponse,
    DocumentSummaryResponse,
    DocumentUploadResponse,
)
from src.shared.customExceptions import BaseApplicationException, ResourceNotFoundException
from src.storage.fileMetadata import read_upload_with_sha256
from src.storage.storageBinding import storage_provider_for
from src.storage.storageProvider import StorageProvider


class DocumentService:
    def __init__(
        self,
        session: AsyncSession,
        settings: AppEnvironment,
        storage: StorageProvider,
    ) -> None:
        self._session = session
        self._settings = settings
        self._storage = storage
        self._repo = DocumentRepository(session)
        self._ingestion_jobs = IngestionJobRepository(session)

    @classmethod
    def from_request(
        cls,
        session: AsyncSession,
        settings: AppEnvironment,
    ) -> Self:
        return cls(session, settings, storage_provider_for(settings))

    async def upload(
        self,
        *,
        upload: UploadFile,
        actor: User,
    ) -> DocumentUploadResponse:
        original = uploadSecurity.normalize_original_filename(upload.filename)
        uploadSecurity.assert_extension_not_blocked(original)
        data, sha256 = await read_upload_with_sha256(
            upload,
            max_bytes=uploadSecurity.MAX_UPLOAD_BYTES,
        )
        uploadSecurity.assert_upload_size(len(data))
        ext, mime = mimeValidator.validate_document_upload(
            original_file_name=original,
            declared_content_type=upload.content_type,
            file_bytes=data,
        )
        stored_name = f"{uuid4().hex}{ext}"
        if not self._settings.cloudinary_configured():
            raise BaseApplicationException(
                "File storage is not configured",
                error_code="storage_not_ready",
                status_code=503,
                details={"provider": "cloudinary"},
            )

        row = Document(
            organization_id=actor.organization_id,
            uploaded_by_user_id=actor.id,
            original_file_name=original,
            stored_file_name=stored_name,
            mime_type=mime,
            file_size=len(data),
            storage_provider="cloudinary",
            storage_path="",
            upload_status="pending",
            content_sha256=sha256,
            parsing_status="pending",
            chunk_count=0,
            embedding_status="pending",
            vector_count=0,
        )
        await self._repo.add(row)
        try:
            path = await self._storage.upload_file(
                organization_id=actor.organization_id,
                document_id=row.id,
                stored_file_name=stored_name,
                data=data,
                content_type=mime,
            )
        except Exception as exc:
            row.upload_status = "failed"
            row.storage_path = ""
            await self._repo.flush()
            raise BaseApplicationException(
                "Upload to storage failed",
                error_code="storage_upload_failed",
                status_code=503,
                details={"reason": str(exc)},
            ) from exc

        row.storage_path = path
        row.upload_status = "stored"
        await self._repo.flush()
        await self._ingestion_jobs.cancel_active_for_document(document_id=row.id)
        job = IngestionJob(
            organization_id=actor.organization_id,
            document_id=row.id,
            status=INGESTION_JOB_PENDING,
        )
        await self._ingestion_jobs.add(job)
        await self._repo.flush()
        await self._session.commit()
        try:
            enqueue_ingestion_job(job_id=job.id)
        except Exception as exc:
            failed = await self._ingestion_jobs.get_by_id(job.id)
            if failed is not None:
                await self._ingestion_jobs.mark_failed(job.id, message=f"enqueue:{exc!s}")
            await self._session.commit()
            raise BaseApplicationException(
                "Ingestion task could not be queued",
                error_code="ingestion_enqueue_failed",
                status_code=503,
                details={"reason": str(exc)},
            ) from exc

        base = DocumentUploadResponse.model_validate(row)
        return base.model_copy(update={"ingestion_job_id": job.id})

    async def cancel_ingestion(
        self,
        *,
        actor: User,
        document_id: UUID,
    ) -> CancelIngestionResponse:
        row = await self._repo.get_by_id_for_org(document_id, actor.organization_id)
        if row is None:
            raise ResourceNotFoundException(
                "Document not found",
                details={"document_id": str(document_id)},
            )
        n = await self._ingestion_jobs.cancel_active_for_document(document_id=document_id)
        return CancelIngestionResponse(document_id=document_id, cancelled_jobs=n)

    async def list_for_actor(
        self,
        *,
        actor: User,
        limit: int,
        offset: int,
    ) -> DocumentListResponse:
        rows = await self._repo.list_for_org(
            actor.organization_id,
            limit=limit,
            offset=offset,
        )
        total = await self._repo.count_for_org(actor.organization_id)
        items = [DocumentSummaryResponse.model_validate(r) for r in rows]
        return DocumentListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    async def get_for_actor(self, *, actor: User, document_id: UUID) -> DocumentSummaryResponse:
        row = await self._repo.get_by_id_for_org(document_id, actor.organization_id)
        if row is None:
            raise ResourceNotFoundException(
                "Document not found",
                details={"document_id": str(document_id)},
            )
        return DocumentSummaryResponse.model_validate(row)
