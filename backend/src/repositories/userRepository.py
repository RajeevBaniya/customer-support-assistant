from uuid import UUID

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.roleModel import Role
from src.models.userModel import User
from src.models.userRolesTable import user_roles_table


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_clerk_id(self, clerk_user_id: str) -> User | None:
        stmt = select(User).where(User.clerk_user_id == clerk_user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_clerk_id_with_org(self, clerk_user_id: str) -> User | None:
        stmt = (
            select(User)
            .options(selectinload(User.organization), selectinload(User.roles))
            .where(User.clerk_user_id == clerk_user_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_role_by_name(self, role_name: str) -> Role | None:
        stmt = select(Role).where(Role.role_name == role_name)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def add(self, user: User) -> User:
        self._session.add(user)
        await self._session.flush()
        return user

    async def attach_role(self, user_id: UUID, role_id: UUID) -> None:
        await self._session.execute(
            insert(user_roles_table).values(user_id=user_id, role_id=role_id)
        )
