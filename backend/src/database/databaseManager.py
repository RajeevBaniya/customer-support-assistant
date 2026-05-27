from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from src.core.appEnvironment import AppEnvironment
from src.database.queryPerformanceTracker import attach_slow_query_logging
from src.database.urlNormalization import resolve_database_urls
from src.observability.structuredLogger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    def __init__(self, settings: AppEnvironment) -> None:
        self._settings = settings
        resolved = resolve_database_urls(settings.database_url)
        self._engine: AsyncEngine = create_async_engine(
            resolved.async_sqlalchemy_url,
            connect_args=resolved.async_connect_args,
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
        except Exception as exc:
            logger.error(
                "database_verify_connection_failed",
                component="database_manager.verify_connection",
                exc_type=type(exc).__name__,
                exc_message=str(exc),
                exc_info=True,
            )
            return False

    async def close(self) -> None:
        await self._engine.dispose()
