import pytest
from pydantic import ValidationError

from core.appEnvironment import AppEnvironment
from database.syncUrl import to_psycopg


def test_database_url_requires_postgresql_asyncpg() -> None:
    with pytest.raises(ValidationError):
        AppEnvironment(
            APP_NAME="RecallStack",
            APP_ENV="development",
            API_PREFIX="/api/v1",
            DEBUG=True,
            BACKEND_PORT=8000,
            DATABASE_URL="mysql://user:pass@localhost:3306/db",
        )


def test_database_url_accepts_asyncpg_driver() -> None:
    config = AppEnvironment(
        APP_NAME="RecallStack",
        APP_ENV="development",
        API_PREFIX="/api/v1",
        DEBUG=True,
        BACKEND_PORT=8000,
        DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/recallstack",
    )
    assert config.database_url.startswith("postgresql+asyncpg://")


def test_asyncpg_url_maps_to_psycopg_sync_driver() -> None:
    async_url = "postgresql+asyncpg://postgres:postgres@localhost:5432/recallstack"
    assert to_psycopg(async_url) == (
        "postgresql+psycopg://postgres:postgres@localhost:5432/recallstack"
    )


def test_asyncpg_url_helper_rejects_non_asyncpg_scheme() -> None:
    with pytest.raises(ValueError):
        to_psycopg("postgresql://localhost/db")
