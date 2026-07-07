from uuid import UUID

from src.retrieval.retrievalRanking import cosine_distance_to_similarity, sort_retrieval_hits
from src.vectorstore.queryHit import VectorQueryHit


def test_cosine_distance_to_similarity_endpoints() -> None:
    assert cosine_distance_to_similarity(0.0) == 1.0
    assert cosine_distance_to_similarity(1.0) == 0.0
    assert cosine_distance_to_similarity(2.0) == 0.0


def test_sort_retrieval_hits_is_deterministic() -> None:
    u1 = UUID("00000000-0000-4000-8000-000000000001")
    u2 = UUID("00000000-0000-4000-8000-000000000002")
    a = VectorQueryHit(
        vector_id="a",
        document_id=u1,
        chunk_index=1,
        distance=0.0,
        text="",
        metadata={},
    )
    b = VectorQueryHit(
        vector_id="b",
        document_id=u1,
        chunk_index=0,
        distance=0.0,
        text="",
        metadata={},
    )
    c = VectorQueryHit(
        vector_id="c",
        document_id=u2,
        chunk_index=0,
        distance=0.0,
        text="",
        metadata={},
    )
    scored = [(a, 0.5), (b, 0.5), (c, 0.8)]
    ordered = sort_retrieval_hits(scored)
    assert [(h.vector_id, s) for h, s in ordered] == [("c", 0.8), ("b", 0.5), ("a", 0.5)]
