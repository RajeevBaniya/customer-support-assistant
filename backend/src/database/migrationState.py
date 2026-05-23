from dataclasses import dataclass
from typing import cast

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine

from core.appEnvironment import BACKEND_ROOT


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
    except Exception:
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
