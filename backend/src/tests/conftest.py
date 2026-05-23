import os
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

_DEFAULT_KEYS: dict[str, str] = {
    "APP_NAME": "RecallStackTests",
    "API_PREFIX": "/api/v1",
    "BACKEND_PORT": "8000",
    "APP_ENV": "test",
    "DEBUG": "false",
    "DATABASE_URL": "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/recallstack",
    "TEST_JWT_SECRET": "unit-test-jwt-secret-at-least-thirty-two-chars",
}
for _key, _value in _DEFAULT_KEYS.items():
    if not os.environ.get(_key, "").strip():
        os.environ[_key] = _value

from main import app  # noqa: E402


@pytest.fixture
async def async_client() -> AsyncIterator[AsyncClient]:
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
