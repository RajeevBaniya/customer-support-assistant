from __future__ import annotations

from src.evaluation.scoring.textSignals import jaccard, sentence_chunks, token_set


def compute_hallucination_score(
    *,
    answer: str,
    context: str,
    faithfulness: float,
    citations_count: int,
    chunk_count: int,
) -> float:
    base = max(0.0, min(1.0, 1.0 - faithfulness))
    penalty = 0.0
    if chunk_count > 0 and citations_count == 0 and answer.strip():
        penalty += 0.25
    sentences = sentence_chunks(answer)
    ctx_lower = context.lower()
    for s in sentences[:24]:
        toks = token_set(s)
        if len(toks) < 6:
            continue
        if jaccard(toks, token_set(context)) < 0.08 and s.lower() not in ctx_lower:
            penalty += 0.03
    score = min(1.0, base + min(0.35, penalty))
    return max(0.0, score)
