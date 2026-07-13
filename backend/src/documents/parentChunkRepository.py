"""Repository managing parent document chunk database persistence."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.parentChunkModel import ParentChunk


class ParentChunkRepository:
    """Repository handling database operations for ParentChunk models."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_all(self, rows: list[ParentChunk]) -> list[ParentChunk]:
        """Bulk persists parent chunk rows."""
        self._session.add_all(rows)
        await self._session.flush()
        return rows

    async def get_by_document_id(self, document_id: UUID) -> list[ParentChunk]:
        """Retrieves parent chunks for a given document."""
        stmt = (
            select(ParentChunk)
            .where(ParentChunk.document_id == document_id)
            .order_by(ParentChunk.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete_by_document_id(self, document_id: UUID) -> int:
        """Deletes parent chunks (and cascades to child chunks) for a document."""
        from sqlalchemy import delete
        stmt = delete(ParentChunk).where(ParentChunk.document_id == document_id)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return int(result.rowcount or 0)
