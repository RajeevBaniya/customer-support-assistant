import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_analytics_tokens_requires_auth(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/analytics/tokens")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_metrics_public(async_client: AsyncClient) -> None:
    response = await async_client.get("/metrics")
    assert response.status_code == 200
    assert "recallstack_http_requests_total" in response.text
