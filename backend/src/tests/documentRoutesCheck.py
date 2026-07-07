from uuid import UUID

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_documents_list_requires_auth(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/documents")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_documents_upload_requires_auth(async_client: AsyncClient) -> None:
    response = await async_client.post(
        "/api/v1/documents/upload",
        files={"file": ("a.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_documents_cancel_ingestion_requires_auth(async_client: AsyncClient) -> None:
    cid = UUID("00000000-0000-4000-8000-000000000099")
    response = await async_client.post(f"/api/v1/documents/{cid}/cancel-ingestion")
    assert response.status_code == 401
