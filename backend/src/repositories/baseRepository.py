from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

TModel = TypeVar("TModel")


class BaseRepository(Generic[TModel]):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, model: type[TModel], entity_id: UUID) -> TModel | None:
        return await self._session.get(model, entity_id)

    async def list_page(
        self,
        model: type[TModel],
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TModel]:
        stmt = select(model).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def add(self, entity: TModel) -> TModel:
        self._session.add(entity)
        await self._session.flush()
        return entity
