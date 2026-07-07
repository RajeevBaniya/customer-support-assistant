import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_evaluation_run_requires_auth(async_client: AsyncClient) -> None:
    response = await async_client.post(
        "/api/v1/evaluation/run",
        json={"query": "hello world there"},
    )
    assert response.status_code == 401
