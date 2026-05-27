from __future__ import annotations

from src.evaluation.scoring.textSignals import (
    best_sentence_overlap,
    jaccard,
    sentence_chunks,
    token_set,
)


def compute_faithfulness_score(
    *,
    answer: str,
    context: str,
    citations_count: int,
    chunk_count: int,
) -> float:
    sentences = sentence_chunks(answer)
    if not sentences:
        return 1.0 if not answer.strip() else 0.0
    overlaps = [best_sentence_overlap(s, context) for s in sentences]
    support_ratio = sum(1 for o in overlaps if o >= 0.12) / max(1, len(overlaps))
    mean_overlap = sum(overlaps) / max(1, len(overlaps))
    if chunk_count <= 0:
        cite_ratio = 1.0 if citations_count == 0 else 0.0
    else:
        cite_ratio = min(1.0, citations_count / max(1, min(3, chunk_count)))
    raw = 0.55 * mean_overlap + 0.25 * support_ratio + 0.2 * cite_ratio
    return max(0.0, min(1.0, raw))


def compute_answer_relevance_score(*, query: str, answer: str) -> float:
    return max(0.0, min(1.0, jaccard(token_set(query), token_set(answer))))
