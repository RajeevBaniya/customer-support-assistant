import os

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_live_probe_returns_200(async_client: AsyncClient) -> None:
    response = await async_client.get("/live")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["probe"] == "live"


@pytest.mark.asyncio
async def test_ready_probe_reflects_database_state(async_client: AsyncClient) -> None:
    response = await async_client.get("/ready")

    assert response.status_code in {200, 503}
    body = response.json()
    db = (
        body["data"]["database"]
        if response.status_code == 200
        else body["error"]["details"]["database"]
    )
    assert "pool" in db
    assert "migrations" in db
    if response.status_code == 200:
        assert body["success"] is True
        assert db["status"] == "up"
        assert db["migrations"]["aligned"] is True
    else:
        assert body["success"] is False
        assert body["error"]["details"]["probe"] == "ready"


@pytest.mark.asyncio
async def test_health_probe_matches_database_state(async_client: AsyncClient) -> None:
    response = await async_client.get("/health")

    assert response.status_code in {200, 503}
    body = response.json()
    if response.status_code == 200:
        db = body["data"]["database"]
        assert db["status"] == "up"
        assert db["migrations"]["aligned"] is True
        assert "pool" in db
        auth = body["data"]["auth"]
        assert "jwt_validation_ready" in auth
        assert body["data"]["environment"] == os.environ["APP_ENV"]
    else:
        assert body["error"]["code"] == "infrastructure_unhealthy"
        assert body["error"]["details"]["probe"] == "health"
