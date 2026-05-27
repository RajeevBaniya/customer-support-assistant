import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import create_engine, pool

from src import models
from src.core.appEnvironment import AppEnvironment
from src.database.databaseBaseModel import Base
from src.database.urlNormalization import resolve_database_urls
from src.evaluation import models as evaluation_models

_ = (models.__spec__, evaluation_models.__spec__)

ROOT = Path(__file__).resolve().parents[1]


def _configure_env() -> None:
    load_dotenv(ROOT / ".env")
    for _key, _val in (
        ("APP_ENV", "development"),
        ("DEBUG", "false"),
    ):
        if not os.environ.get(_key, "").strip():
            os.environ[_key] = _val


_configure_env()

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_sync_url() -> str:
    settings = AppEnvironment()  # type: ignore[call-arg]
    return resolve_database_urls(settings.database_url).sync_alembic_url


def run_migrations_offline() -> None:
    context.configure(
        url=get_sync_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(get_sync_url(), poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
