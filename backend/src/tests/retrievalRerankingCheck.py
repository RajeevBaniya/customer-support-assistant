from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from uuid import UUID

from src.models.documentModel import Document
from src.retrieval.reranking import run_rerank_dedupe_pipeline
from src.vectorstore.queryHit import VectorQueryHit


def _doc(age_days: float) -> MagicMock:
    m = MagicMock(spec=Document)
    m.created_at = datetime.now(UTC) - timedelta(days=age_days)
    return m


def test_rerank_pipeline_deterministic_order() -> None:
    uid = UUID("00000000-0000-4000-8000-000000000010")
    h0 = VectorQueryHit(
        vector_id="v0",
        document_id=uid,
        chunk_index=0,
        distance=0.2,
        text="alpha beta gamma pool redis sizing",
        metadata={},
    )
    h1 = VectorQueryHit(
        vector_id="v1",
        document_id=uid,
        chunk_index=1,
        distance=0.2,
        text="alpha beta gamma pool redis sizing extra",
        metadata={},
    )
    doc_map = {uid: _doc(5.0)}
    now = datetime.now(UTC)
    scored = [(h0, 0.75), (h1, 0.74)]
    a = run_rerank_dedupe_pipeline(scored, query="redis pool sizing", doc_map=doc_map, now=now)
    b = run_rerank_dedupe_pipeline(scored, query="redis pool sizing", doc_map=doc_map, now=now)
    assert [x[0].chunk_index for x in a.hits] == [x[0].chunk_index for x in b.hits]


def test_near_duplicate_chunk_suppressed() -> None:
    uid = UUID("00000000-0000-4000-8000-000000000011")
    same = "identical chunk body for near duplicate test here"
    h0 = VectorQueryHit(
        vector_id="a",
        document_id=uid,
        chunk_index=0,
        distance=0.1,
        text=same,
        metadata={},
    )
    h1 = VectorQueryHit(
        vector_id="b",
        document_id=uid,
        chunk_index=1,
        distance=0.09,
        text=same,
        metadata={},
    )
    doc_map = {uid: _doc(1.0)}
    now = datetime.now(UTC)
    pipe = run_rerank_dedupe_pipeline(
        [(h0, 0.9), (h1, 0.88)],
        query="chunk",
        doc_map=doc_map,
        now=now,
    )
    assert len(pipe.hits) == 1
    assert pipe.near_dup_dropped >= 1


def test_rrf_rank_fusion_and_bm25_flow() -> None:
    from src.core.appEnvironment import AppEnvironment

    settings = AppEnvironment(
        APP_ENV="test",
        DEBUG=False,
        DATABASE_URL="postgresql+asyncpg://u:p@localhost/db",
        HYBRID_RETRIEVAL_ENABLED=True,
        RRF_K=60,
    )
    uid = UUID("00000000-0000-4000-8000-000000000012")
    # h0 matches query keyword 'elasticsearch', h1 does not but has higher semantic similarity
    h0 = VectorQueryHit(
        vector_id="v0",
        document_id=uid,
        chunk_index=0,
        distance=0.3,
        text="we run elasticsearch on staging servers",
        metadata={},
    )
    h1 = VectorQueryHit(
        vector_id="v1",
        document_id=uid,
        chunk_index=1,
        distance=0.1,
        text="completely unrelated text query with high dummy score",
        metadata={},
    )
    doc_map = {uid: _doc(1.0)}
    now = datetime.now(UTC)

    # h1 is ranked 1st in dense (sim=0.9), h0 is ranked 2nd (sim=0.7)
    # in sparse BM25, h0 matches 'elasticsearch' so ranked 1st, h1 is 2nd (no matching tokens)
    scored = [(h0, 0.7), (h1, 0.9)]
    pipe = run_rerank_dedupe_pipeline(
        scored,
        query="elasticsearch",
        doc_map=doc_map,
        now=now,
        settings=settings,
    )
    # verify RRF scoring and execution order
    assert len(pipe.hits) == 2
    # h0: dense rank=2, sparse rank=1 -> RRF = 1/(60+2) + 1/(60+1) = 1/62 + 1/61 = 0.016129 + 0.016393 = 0.03252
    # h1: dense rank=1, sparse rank=2 -> RRF = 1/(60+1) + 1/(60+2) = 1/61 + 1/62 = 0.03252
    # they should have identical base RRF scores, but h0 has phrase match lexical boost
    # (since 'elasticsearch' is in h0.text), so h0 will win composite score
    assert pipe.hits[0][0].vector_id == "v0"

