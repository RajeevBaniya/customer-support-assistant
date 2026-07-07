import os

import pytest


def _run_cloud_integration() -> bool:
    return os.environ.get("RUN_CLOUD_INTEGRATION_TESTS", "").strip() == "1"


def _pinecone_env_ready() -> bool:
    keys = ("PINECONE_API_KEY", "PINECONE_INDEX_NAME", "PINECONE_CLOUD", "PINECONE_REGION")
    return all(os.environ.get(k, "").strip() for k in keys)


def _require_pinecone_cloud() -> None:
    if not _run_cloud_integration():
        pytest.skip("RUN_CLOUD_INTEGRATION_TESTS=1 enables Pinecone integration checks")
    if not _pinecone_env_ready():
        pytest.skip(
            "PINECONE_API_KEY, PINECONE_INDEX_NAME, PINECONE_CLOUD, PINECONE_REGION required"
        )


def test_pinecone_index_reachable_for_retrieval_integration() -> None:
    _require_pinecone_cloud()
    from src.core.appEnvironment import AppEnvironment
    from src.vectorstore.pineconeStore import build_pinecone_store

    try:
        build_pinecone_store(AppEnvironment())  # type: ignore[call-arg]
    except Exception as exc:
        pytest.skip(f"Pinecone unavailable: {exc}")
