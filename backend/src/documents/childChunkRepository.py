"""Repository managing child document chunk database persistence."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.childChunkModel import ChildChunk


class ChildChunkRepository:
    """Repository handling database operations for ChildChunk models."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_all(self, rows: list[ChildChunk]) -> list[ChildChunk]:
        """Bulk persists child chunk rows."""
        self._session.add_all(rows)
        await self._session.flush()
        return rows

    async def get_by_document_id(self, document_id: UUID) -> list[ChildChunk]:
        """Retrieves child chunks for a given document."""
        stmt = (
            select(ChildChunk)
            .where(ChildChunk.document_id == document_id)
            .order_by(ChildChunk.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete_by_document_id(self, document_id: UUID) -> int:
        """Deletes child chunks for a document."""
        from sqlalchemy import delete
        stmt = delete(ChildChunk).where(ChildChunk.document_id == document_id)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return int(result.rowcount or 0)
