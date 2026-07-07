from src.evaluation.scoring.evaluationScoreBundle import compute_evaluation_scores


def test_compute_evaluation_scores_deterministic() -> None:
    refs = [
        {
            "document_id": "00000000-0000-4000-8000-000000000001",
            "chunk_index": 0,
            "document_name": "a.pdf",
            "similarity_score": 0.8,
        }
    ]
    out = compute_evaluation_scores(
        query="what is x",
        answer="x is described in the context block here.",
        context="this context block defines x as a test token.",
        chunk_refs=refs,
        citations_count=1,
        top_k=5,
    )
    keys = {
        "faithfulness_score",
        "hallucination_score",
        "retrieval_relevance_score",
        "answer_relevance_score",
    }
    assert keys == set(out.keys())
    assert 0.0 <= out["faithfulness_score"] <= 1.0
    assert 0.0 <= out["hallucination_score"] <= 1.0
    assert out == compute_evaluation_scores(
        query="what is x",
        answer="x is described in the context block here.",
        context="this context block defines x as a test token.",
        chunk_refs=refs,
        citations_count=1,
        top_k=5,
    )


def test_empty_chunks_zero_retrieval_score() -> None:
    out = compute_evaluation_scores(
        query="q",
        answer="a",
        context="",
        chunk_refs=[],
        citations_count=0,
        top_k=3,
    )
    assert out["retrieval_relevance_score"] == 0.0
