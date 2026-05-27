from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.conversationModel import Conversation


class ConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, row: Conversation) -> Conversation:
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_for_user(
        self,
        conversation_id: UUID,
        *,
        organization_id: UUID,
        user_id: UUID,
    ) -> Conversation | None:
        stmt = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.organization_id == organization_id,
            Conversation.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        limit: int,
        offset: int,
    ) -> list[Conversation]:
        stmt = (
            select(Conversation)
            .where(
                Conversation.organization_id == organization_id,
                Conversation.user_id == user_id,
            )
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_for_user(self, *, organization_id: UUID, user_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Conversation)
            .where(
                Conversation.organization_id == organization_id,
                Conversation.user_id == user_id,
            )
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def touch_updated_at(self, conversation_id: UUID) -> None:
        stmt = (
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(updated_at=func.now())
        )
        await self._session.execute(stmt)
