from datetime import datetime
from uuid import UUID

from pydantic import Field

from src.schemas.commonSchemas import ApiModel


class DocumentUploadResponse(ApiModel):
    id: UUID
    organization_id: UUID
    uploaded_by_user_id: UUID
    original_file_name: str
    stored_file_name: str
    mime_type: str
    file_size: int
    storage_provider: str
    storage_path: str
    upload_status: str
    content_sha256: str
    created_at: datetime
    parsing_status: str
    parsed_at: datetime | None
    parser_type: str | None
    chunk_count: int
    embedding_status: str
    embedded_at: datetime | None
    embedding_model: str | None
    vector_count: int
    ingestion_job_id: UUID


class CancelIngestionResponse(ApiModel):
    document_id: UUID
    cancelled_jobs: int


class DocumentSummaryResponse(ApiModel):
    id: UUID
    organization_id: UUID
    uploaded_by_user_id: UUID
    original_file_name: str
    stored_file_name: str
    mime_type: str
    file_size: int
    storage_provider: str
    storage_path: str
    upload_status: str
    content_sha256: str
    created_at: datetime
    updated_at: datetime
    parsing_status: str
    parsed_at: datetime | None
    parser_type: str | None
    chunk_count: int
    embedding_status: str
    embedded_at: datetime | None
    embedding_model: str | None
    vector_count: int


class DocumentListResponse(ApiModel):
    items: list[DocumentSummaryResponse]
    total: int
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
