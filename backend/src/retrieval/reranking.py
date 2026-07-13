from __future__ import annotations

import re
import time
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from rank_bm25 import BM25Okapi  # type: ignore

from src.core.appEnvironment import AppEnvironment
from src.models.documentModel import Document
from src.observability.metrics.recorders import record_hybrid_retrieval
from src.vectorstore.queryHit import VectorQueryHit

_TOKEN = re.compile(r"[a-z0-9]+", re.I)

PHRASE_SUBSTRING_BOOST = 0.022
TOKEN_MATCH_PER_TOKEN = 0.005
TOKEN_MATCH_CAP = 0.036
RECENCY_BOOST_MAX = 0.032
RECENCY_SCALE_DAYS = 120.0
SEMANTIC_WEIGHT = 1.0
NEAR_DUP_JACCARD = 0.88
MIN_TOKEN_LEN = 3


@dataclass(frozen=True)
class RerankPipelineResult:
    hits: list[tuple[VectorQueryHit, float]]
    rerank_input_count: int
    after_dedup_count: int
    near_dup_dropped: int
    rerank_ms: float


def _tokens(text: str) -> set[str]:
    return {m.group(0).lower() for m in _TOKEN.finditer(text) if len(m.group(0)) >= MIN_TOKEN_LEN}


def _recency_boost(doc: Document, now: datetime) -> float:
    created = doc.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    age_days = max(0.0, (now - created).total_seconds() / 86400.0)
    freshness = 1.0 - min(age_days / RECENCY_SCALE_DAYS, 1.0)
    return RECENCY_BOOST_MAX * freshness


def _lexical_boost(hit: VectorQueryHit, query_lower: str, query_tokens: set[str]) -> float:
    low = hit.text.lower()
    boost = 0.0
    if len(query_lower) >= 4 and query_lower in low:
        boost += PHRASE_SUBSTRING_BOOST
    if query_tokens:
        overlap = len(query_tokens & _tokens(hit.text))
        boost += min(TOKEN_MATCH_CAP, overlap * TOKEN_MATCH_PER_TOKEN)
    return boost


def _composite(
    base_sim: float,
    hit: VectorQueryHit,
    query_lower: str,
    query_tokens: set[str],
    doc: Document,
    now: datetime,
) -> float:
    extra = _lexical_boost(hit, query_lower, query_tokens) + _recency_boost(doc, now)
    return min(1.0, max(0.0, SEMANTIC_WEIGHT * float(base_sim) + extra))


def _jaccard(a: str, b: str) -> float:
    wa, wb = _tokens(a), _tokens(b)
    if not wa and not wb:
        return 1.0
    if not wa or not wb:
        return 0.0
    inter = len(wa & wb)
    union = len(wa | wb)
    return float(inter) / float(union) if union else 0.0


def run_rerank_dedupe_pipeline(
    ready_scored: list[tuple[VectorQueryHit, float]],
    *,
    query: str,
    doc_map: Mapping[UUID, Document],
    now: datetime,
    settings: AppEnvironment | None = None,
) -> RerankPipelineResult:
    t0 = time.perf_counter()
    if not ready_scored:
        return RerankPipelineResult([], 0, 0, 0, 0.0)

    if settings is not None and settings.hybrid_retrieval_enabled:
        t_rrf0 = time.perf_counter()
        corpus = [hit.text for hit, _ in ready_scored]
        tokenized_corpus = [list(_tokens(txt)) for txt in corpus]
        bm25 = BM25Okapi(tokenized_corpus)
        tokenized_query = list(_tokens(query))
        bm25_scores = bm25.get_scores(tokenized_query)

        dense_sorted_indices = sorted(
            range(len(ready_scored)),
            key=lambda idx: (-ready_scored[idx][1], idx),
        )
        sparse_sorted_indices = sorted(
            range(len(ready_scored)),
            key=lambda idx: (-bm25_scores[idx], idx),
        )

        dense_ranks = {idx: rank for rank, idx in enumerate(dense_sorted_indices, start=1)}
        sparse_ranks = {idx: rank for rank, idx in enumerate(sparse_sorted_indices, start=1)}

        rrf_k = settings.rrf_k
        rrf_scores: list[float] = []
        for idx in range(len(ready_scored)):
            dr = dense_ranks[idx]
            sr = sparse_ranks[idx]
            score = 1.0 / (rrf_k + dr) + 1.0 / (rrf_k + sr)
            rrf_scores.append(score)

        ready_scored = [
            (ready_scored[idx][0], rrf_scores[idx])
            for idx in range(len(ready_scored))
        ]
        duration_s = time.perf_counter() - t_rrf0
        record_hybrid_retrieval(pool_size=len(ready_scored), duration_s=duration_s)

    qlow = query.strip().lower()
    qtok = _tokens(query)
    enriched: list[tuple[VectorQueryHit, float, float]] = []
    for hit, sim in ready_scored:
        doc = doc_map.get(hit.document_id)
        if doc is None:
            continue
        enriched.append((hit, sim, _composite(sim, hit, qlow, qtok, doc, now)))
    enriched.sort(key=lambda row: (-row[2], str(row[0].document_id), row[0].chunk_index))
    kept: list[tuple[VectorQueryHit, float]] = []
    norms: list[str] = []
    dropped = 0
    for hit, sim, _ in enriched:
        norm = " ".join(hit.text.lower().split())
        if any(_jaccard(norm, prev) >= NEAR_DUP_JACCARD for prev in norms):
            dropped += 1
            continue
        kept.append((hit, sim))
        norms.append(norm)
    ms = round((time.perf_counter() - t0) * 1000.0, 3)
    return RerankPipelineResult(
        hits=kept,
        rerank_input_count=len(ready_scored),
        after_dedup_count=len(kept),
        near_dup_dropped=dropped,
        rerank_ms=ms,
    )
