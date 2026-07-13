"""StorageTool wrapping document metadata and file retrieval storage operations."""

from uuid import UUID

from pydantic import BaseModel, Field

from src.documents.documentRepository import DocumentRepository
from src.models.documentModel import Document
from src.runtimeTools.baseTool import BaseTool
from src.storage.storageBinding import storage_provider_for


class LoadDocumentRequest(BaseModel):
    """Schema for loading a document metadata profile."""

    document_id: UUID
    organization_id: UUID


class ListDocumentsRequest(BaseModel):
    """Schema for listing documents in an organization."""

    organization_id: UUID
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)


class RetrieveFileRequest(BaseModel):
    """Schema for fetching raw binary content from store."""

    organization_id: UUID
    storage_path: str = Field(min_length=1)


class StorageTool(BaseTool):
    """Document profile metadata and file retrieval storage tool."""

    async def load_document(
        self, request: LoadDocumentRequest
    ) -> Document | None:
        """Retrieve document metadata."""
        repository = DocumentRepository(self._session)
        return await repository.get_by_id_for_org(
            request.document_id,
            organization_id=request.organization_id,
        )

    async def list_documents(
        self, request: ListDocumentsRequest
    ) -> list[Document]:
        """List document records in an organization."""
        repository = DocumentRepository(self._session)
        return await repository.list_for_org(
            request.organization_id,
            limit=request.limit,
            offset=request.offset,
        )

    async def count_documents(self, organization_id: UUID) -> int:
        """Count total documents in an organization."""
        repository = DocumentRepository(self._session)
        return await repository.count_for_org(organization_id)

    async def retrieve_file(self, request: RetrieveFileRequest) -> bytes:
        """Fetch raw binary content from storage."""
        provider = storage_provider_for(self._settings)
        return await provider.get_file(
            organization_id=request.organization_id,
            storage_path=request.storage_path,
        )
