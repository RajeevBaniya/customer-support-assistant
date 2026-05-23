from typing import Any

from fastapi import Request

from database.databaseManager import DatabaseManager
from database.migrationState import MigrationReport
from database.pool_metrics import pool_snapshot


async def db_section(request: Request) -> dict[str, Any]:
    database_manager: DatabaseManager = request.app.state.database_manager
    migration_report: MigrationReport = request.app.state.migration_report
    connected = await database_manager.verify_connection()
    pool = pool_snapshot(database_manager.engine)
    migrations = {
        "aligned": migration_report.aligned,
        "current_revision": migration_report.current_revision,
        "head_revision": migration_report.head_revision,
    }
    return {
        "status": "up" if connected else "down",
        "pool": pool,
        "migrations": migrations,
    }


def is_db_ready(bundle: dict[str, Any]) -> bool:
    return bundle["status"] == "up" and bool(bundle["migrations"]["aligned"])
