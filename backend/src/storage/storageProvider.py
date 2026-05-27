from typing import Protocol
from uuid import UUID


class StorageProvider(Protocol):
    async def upload_file(
        self,
        *,
        organization_id: UUID,
        document_id: UUID,
        stored_file_name: str,
        data: bytes,
        content_type: str,
    ) -> str:
        """Persist bytes; return Cloudinary public_id (no URL)."""

    async def delete_file(self, *, organization_id: UUID, storage_path: str) -> None:
        """Best-effort removal."""

    async def get_file(self, *, organization_id: UUID, storage_path: str) -> bytes:
        """Load object bytes."""

    async def file_exists(self, *, organization_id: UUID, storage_path: str) -> bool:
        """Whether object exists."""
