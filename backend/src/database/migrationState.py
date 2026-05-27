from dataclasses import dataclass
from typing import cast

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine

from src.core.appEnvironment import BACKEND_ROOT
from src.observability.structuredLogger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class MigrationReport:
    aligned: bool
    current_revision: str | None
    head_revision: str | None


def get_current_revision(sync_connection: object) -> str | None:
    connection = cast(Connection, sync_connection)
    context = MigrationContext.configure(connection)
    return context.get_current_revision()


async def inspect_migration_state(engine: AsyncEngine) -> MigrationReport:
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    head_revision = script.get_current_head()
    try:
        async with engine.connect() as connection:
            current_revision = await connection.run_sync(get_current_revision)
    except Exception as exc:
        logger.error(
            "migration_state_inspect_failed",
            component="migration_state.inspect_migration_state",
            exc_type=type(exc).__name__,
            exc_message=str(exc),
            exc_info=True,
        )
        return MigrationReport(
            aligned=False,
            current_revision=None,
            head_revision=head_revision,
        )
    aligned = bool(
        current_revision is not None
        and head_revision is not None
        and current_revision == head_revision,
    )
    return MigrationReport(
        aligned=aligned,
        current_revision=current_revision,
        head_revision=head_revision,
    )
