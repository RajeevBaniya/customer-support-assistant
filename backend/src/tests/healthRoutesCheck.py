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
        storage = body["data"]["storage"]
        assert "provider" in storage
        assert "writable" in storage
        redis = body["data"]["redis"]
        assert "redis_configured" in redis
        assert "redis_reachable" in redis
        assert "streaming_ready" in redis
        parsing = body["data"]["parsing"]
        assert "supported_mime_types" in parsing
        assert "parsers" in parsing
        assert "ready" in parsing
        vector = body["data"]["vector"]
        assert "pinecone_configured" in vector
        assert "pinecone_reachable" in vector
        assert "embedding_model" in vector
        assert "embedding_batch_size" in vector
        retrieval = body["data"]["retrieval"]
        assert "retrieval_enabled" in retrieval
        assert "vector_search_ready" in retrieval
        assert "pinecone_query_ready" in retrieval
        assert retrieval["reranking_ready"] is True
        assert retrieval["retrieval_pipeline_ready"] is retrieval["vector_search_ready"]
        rag = body["data"]["rag"]
        assert "active_llm_provider" in rag
        assert "groq_ready" in rag
        assert "gemini_ready" in rag
        assert "retrieval_ready" in rag
        wf = body["data"]["workflow"]
        assert "workflow_engine_ready" in wf
        assert "graph_registry_ready" in wf
        ev = body["data"]["evaluation"]
        assert "evaluation_engine_ready" in ev
        assert "benchmark_registry_ready" in ev
        obs = body["data"]["observability"]
        assert obs.get("metrics_ready") is True
        assert obs.get("tracing_ready") is True
        assert obs.get("observability_ready") is True
        dep = body["data"]["deployment"]
        assert "deployment_ready" in dep
        assert "missing_requirements" in dep
        assert "warnings" in dep
        assert "streaming_ready" in body["data"]
        assert body["data"]["streaming_ready"] is body["data"]["redis"]["streaming_ready"]
        celery = body["data"]["celery"]
        assert "celery_configured" in celery
        assert "celery_broker_ok" in celery
        assert "celery_worker_ping" in celery
        assert "ingestion_pipeline_ready" in celery
        assert body["data"]["environment"] == os.environ["APP_ENV"]
    else:
        assert body["error"]["code"] == "infrastructure_unhealthy"
        assert body["error"]["details"]["probe"] == "health"
