from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from core.appEnvironment import AppEnvironment
from database.queryPerformanceTracker import attach_slow_query_logging


class DatabaseManager:
    def __init__(self, settings: AppEnvironment) -> None:
        self._settings = settings
        self._engine: AsyncEngine = create_async_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_timeout=settings.database_pool_timeout,
            pool_recycle=settings.database_pool_recycle,
        )
        attach_slow_query_logging(self._engine)

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    async def verify_connection(self) -> bool:
        try:
            async with self._engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    async def close(self) -> None:
        await self._engine.dispose()
