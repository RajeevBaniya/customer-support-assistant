from __future__ import annotations

from typing import Any


def compute_retrieval_relevance_score(
    *,
    chunk_refs: list[dict[str, Any]],
    top_k: int,
) -> float:
    if not chunk_refs:
        return 0.0
    sims = [float(x.get("similarity_score") or 0.0) for x in chunk_refs]
    avg_sim = sum(sims) / max(1, len(sims))
    doc_ids = {str(x.get("document_id")) for x in chunk_refs}
    diversity = len(doc_ids) / max(1, len(chunk_refs))
    tk = top_k if top_k > 0 else len(chunk_refs)
    sufficiency = min(1.0, len(chunk_refs) / max(1, tk))
    pairs = {(str(x.get("document_id")), int(x.get("chunk_index") or -1)) for x in chunk_refs}
    dedupe = len(pairs) / max(1, len(chunk_refs))
    raw = 0.45 * avg_sim + 0.25 * diversity + 0.2 * sufficiency + 0.1 * dedupe
    return max(0.0, min(1.0, raw))
