import os

import pytest
from httpx import ASGITransport, AsyncClient


def _ensure_test_env() -> None:
    defaults: dict[str, str] = {
        "APP_ENV": "test",
        "DEBUG": "false",
        "DATABASE_URL": "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/recallstack",
        "TEST_JWT_SECRET": "unit-test-jwt-secret-at-least-thirty-two-chars",
    }
    for key, value in defaults.items():
        if not os.environ.get(key, "").strip():
            os.environ[key] = value


@pytest.fixture(scope="session")
def _asgi_app():
    _ensure_test_env()
    from src.main import app

    return app


@pytest.fixture
async def async_client(_asgi_app):
    async with _asgi_app.router.lifespan_context(_asgi_app):
        transport = ASGITransport(app=_asgi_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
