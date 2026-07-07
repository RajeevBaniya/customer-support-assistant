import pytest
from pydantic import ValidationError

from src.core.appEnvironment import AppEnvironment
from src.database.urlNormalization import resolve_database_urls


def test_database_url_requires_postgresql_asyncpg() -> None:
    with pytest.raises(ValidationError):
        AppEnvironment(
            APP_ENV="development",
            DEBUG=True,
            DATABASE_URL="mysql://user:pass@localhost:3306/db",
        )


def test_database_url_accepts_asyncpg_driver() -> None:
    config = AppEnvironment(
        APP_ENV="development",
        DEBUG=True,
        DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/recallstack",
    )
    assert config.database_url.startswith("postgresql+asyncpg://")
    assert config.app_name == "RecallStack"
    assert config.api_prefix == "/api/v1"
    assert config.backend_port == 8000


def test_resolve_sync_url_psycopg_preserves_query() -> None:
    async_url = "postgresql+asyncpg://postgres:postgres@localhost:5432/recallstack"
    resolved = resolve_database_urls(async_url)
    assert resolved.sync_alembic_url == (
        "postgresql+psycopg://postgres:postgres@localhost:5432/recallstack"
    )


def test_resolve_rejects_non_asyncpg_scheme() -> None:
    with pytest.raises(ValueError):
        resolve_database_urls("postgresql://localhost/db")
