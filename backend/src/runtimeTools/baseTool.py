"""Base runtime tool class defining database and settings context dependencies."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.appEnvironment import AppEnvironment


class BaseTool:
    """Base class for all runtime tools in the platform."""

    def __init__(self, session: AsyncSession, settings: AppEnvironment) -> None:
        self._session = session
        self._settings = settings
