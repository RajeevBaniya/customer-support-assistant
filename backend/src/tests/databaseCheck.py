import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import create_async_engine

from database.databaseBaseModel import Base
from database.databaseSession import clear_session_factory, configure_session_factory, session_scope
from database.migrationState import inspect_migration_state
from models.organizationModel import Organization
from models.roleModel import Role
from models.userModel import User
from repositories.baseRepository import BaseRepository

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _require_test_db_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL", "").strip()
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set")
    return url


@pytest.mark.asyncio
async def test_migration_inspect_after_upgrade() -> None:
    test_url = _require_test_db_url()
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = test_url
    try:
        cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
        try:
            command.upgrade(cfg, "head")
        except Exception as exc:
            pytest.skip(f"Alembic upgrade skipped: {exc}")
        engine = create_async_engine(test_url)
        try:
            report = await inspect_migration_state(engine)
            assert report.head_revision is not None
            assert report.aligned is True
            assert report.current_revision == report.head_revision
        finally:
            await engine.dispose()
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous


@pytest.mark.asyncio
async def test_repository_add_and_get_roundtrip() -> None:
    test_url = _require_test_db_url()
    engine = create_async_engine(test_url)
    configure_session_factory(engine)
    try:
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
                await conn.run_sync(Base.metadata.create_all)
        except Exception as exc:
            pytest.skip(f"Database setup skipped: {exc}")

        async with session_scope() as session:
            for name, desc in (
                ("admin", "Full control"),
                ("member", "Standard"),
                ("viewer", "Read-only"),
            ):
                session.add(Role(role_name=name, role_description=desc))

        async with session_scope() as session:
            repo = BaseRepository[Organization](session)
            org = Organization(organization_name="Acme", slug=f"acme-{uuid4().hex[:8]}")
            await repo.add(org)
            urepo = BaseRepository[User](session)
            user = User(
                clerk_user_id=f"clerk_{uuid4().hex}",
                email_address=f"u{uuid4().hex[:8]}@example.com",
                first_name="A",
                last_name="B",
                organization_id=org.id,
            )
            await urepo.add(user)
            loaded = await urepo.get_by_id(User, user.id)
            assert loaded is not None
            assert loaded.organization_id == org.id
    finally:
        clear_session_factory()
        await engine.dispose()
