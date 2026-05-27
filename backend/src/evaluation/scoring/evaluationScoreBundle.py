from __future__ import annotations

from src.evaluation.scoring.groundingScore import (
    compute_answer_relevance_score,
    compute_faithfulness_score,
)
from src.evaluation.scoring.hallucinationHeuristics import compute_hallucination_score
from src.evaluation.scoring.retrievalQualityScore import compute_retrieval_relevance_score


def compute_evaluation_scores(
    *,
    query: str,
    answer: str,
    context: str,
    chunk_refs: list[dict[str, object]],
    citations_count: int,
    top_k: int,
) -> dict[str, float]:
    chunk_count = len(chunk_refs)
    faithfulness = compute_faithfulness_score(
        answer=answer,
        context=context,
        citations_count=citations_count,
        chunk_count=chunk_count,
    )
    hallucination = compute_hallucination_score(
        answer=answer,
        context=context,
        faithfulness=faithfulness,
        citations_count=citations_count,
        chunk_count=chunk_count,
    )
    retrieval_rel = compute_retrieval_relevance_score(chunk_refs=chunk_refs, top_k=top_k)
    answer_rel = compute_answer_relevance_score(query=query, answer=answer)
    return {
        "faithfulness_score": faithfulness,
        "hallucination_score": hallucination,
        "retrieval_relevance_score": retrieval_rel,
        "answer_relevance_score": answer_rel,
    }
