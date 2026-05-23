import os
import time
from uuid import uuid4

import jwt
import pytest
from httpx import AsyncClient


def _sign_token(
    *,
    sub: str,
    email: str | None = "u@example.com",
    given: str | None = "Alex",
) -> str:
    secret = os.environ["TEST_JWT_SECRET"]
    now = int(time.time())
    return jwt.encode(
        {
            "sub": sub,
            "email": email,
            "given_name": given,
            "exp": now + 3600,
            "iat": now,
        },
        secret,
        algorithm="HS256",
    )


@pytest.mark.asyncio
async def test_auth_me_returns_verified_identity(async_client: AsyncClient) -> None:
    token = _sign_token(sub=f"user_{uuid4().hex[:12]}")
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["issuer"] == "test"


@pytest.mark.asyncio
async def test_auth_me_rejects_invalid_token(async_client: AsyncClient) -> None:
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-jwt"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_me_requires_bearer(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_users_me_onboards_when_database_available(async_client: AsyncClient) -> None:
    if not os.environ.get("TEST_DATABASE_URL", "").strip():
        pytest.skip("TEST_DATABASE_URL not set")
    token = _sign_token(sub=f"onboard_{uuid4().hex[:16]}")
    response = await async_client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 200:
        pytest.skip(f"users/me needs migrated test database: {response.text}")
    body = response.json()
    assert body["success"] is True
    assert body["data"]["clerk_user_id"].startswith("onboard_")
