"""Repository managing parser and ingestion execution run metrics persistence."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.ingestionMetadataModel import IngestionMetadata


class IngestionMetadataRepository:
    """Repository handling database operations for IngestionMetadata models."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, row: IngestionMetadata) -> IngestionMetadata:
        """Persists a new IngestionMetadata row."""
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_by_document_id(self, document_id: UUID) -> IngestionMetadata | None:
        """Retrieves ingestion metadata for a given document."""
        stmt = select(IngestionMetadata).where(
            IngestionMetadata.document_id == document_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_by_document_id(self, document_id: UUID) -> int:
        """Deletes ingestion metadata for a document."""
        from sqlalchemy import delete
        stmt = delete(IngestionMetadata).where(
            IngestionMetadata.document_id == document_id
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return int(result.rowcount or 0)
