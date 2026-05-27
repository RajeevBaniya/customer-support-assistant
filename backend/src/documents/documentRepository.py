from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.documentModel import Document


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, row: Document) -> Document:
        self._session.add(row)
        await self._session.flush()
        return row

    async def flush(self) -> None:
        await self._session.flush()

    async def get_by_id_for_org(self, document_id: UUID, organization_id: UUID) -> Document | None:
        stmt = select(Document).where(
            Document.id == document_id,
            Document.organization_id == organization_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_org(
        self,
        organization_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> list[Document]:
        stmt = (
            select(Document)
            .where(Document.organization_id == organization_id)
            .order_by(Document.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_for_org(self, organization_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Document)
            .where(
                Document.organization_id == organization_id,
            )
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def map_by_ids_for_org(
        self,
        organization_id: UUID,
        document_ids: list[UUID],
    ) -> dict[UUID, Document]:
        if not document_ids:
            return {}
        stmt = select(Document).where(
            Document.organization_id == organization_id,
            Document.id.in_(document_ids),
        )
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        return {row.id: row for row in rows}
