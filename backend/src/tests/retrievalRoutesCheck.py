import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_retrieval_search_requires_auth(async_client: AsyncClient) -> None:
    response = await async_client.post(
        "/api/v1/retrieval/search",
        json={"query": "hello world"},
    )
    assert response.status_code == 401
