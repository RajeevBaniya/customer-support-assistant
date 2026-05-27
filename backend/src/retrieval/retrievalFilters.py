from src.models.documentModel import Document
from src.vectorstore.queryHit import VectorQueryHit


def document_is_retrieval_ready(row: Document | None) -> bool:
    if row is None:
        return False
    if row.upload_status != "stored":
        return False
    if row.parsing_status != "parsed":
        return False
    if row.embedding_status != "embedded":
        return False
    return True


def passes_similarity(score: float, minimum: float) -> bool:
    return score >= minimum


def filter_scored_hits(
    scored: list[tuple[VectorQueryHit, float]],
    *,
    minimum_similarity: float,
) -> list[tuple[VectorQueryHit, float]]:
    return [pair for pair in scored if passes_similarity(pair[1], minimum_similarity)]
