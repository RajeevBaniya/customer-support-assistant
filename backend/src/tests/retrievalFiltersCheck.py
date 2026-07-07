from uuid import UUID

from src.retrieval.retrievalFilters import document_is_retrieval_ready, filter_scored_hits
from src.vectorstore.queryHit import VectorQueryHit


def test_document_is_retrieval_ready_rejects_none() -> None:
    assert document_is_retrieval_ready(None) is False


def test_document_is_retrieval_ready_rejects_wrong_pipeline() -> None:
    from unittest.mock import MagicMock

    row = MagicMock(spec=["upload_status", "parsing_status", "embedding_status"])
    row.upload_status = "failed"
    row.parsing_status = "parsed"
    row.embedding_status = "embedded"
    assert document_is_retrieval_ready(row) is False


def test_filter_scored_hits_respects_floor() -> None:
    u = UUID("00000000-0000-4000-8000-000000000001")
    h1 = VectorQueryHit(
        vector_id="a",
        document_id=u,
        chunk_index=0,
        distance=0.0,
        text="",
        metadata={},
    )
    h2 = VectorQueryHit(
        vector_id="b",
        document_id=u,
        chunk_index=1,
        distance=0.0,
        text="",
        metadata={},
    )
    out = filter_scored_hits([(h1, 0.9), (h2, 0.1)], minimum_similarity=0.2)
    assert len(out) == 1
    assert out[0][1] == 0.9
