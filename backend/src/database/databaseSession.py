from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

_session_factory: async_sessionmaker[AsyncSession] | None = None


def configure_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    global _session_factory
    _session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    return _session_factory


def clear_session_factory() -> None:
    global _session_factory
    _session_factory = None


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("Session factory is not configured")
    return _session_factory


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except BaseException:
            await session.rollback()
            raise


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with session_scope() as session:
        yield session
