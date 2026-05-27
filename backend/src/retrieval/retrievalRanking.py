from src.vectorstore.queryHit import VectorQueryHit


def cosine_distance_to_similarity(distance: float) -> float:
    sim = 1.0 - float(distance)
    if sim < 0.0:
        return 0.0
    if sim > 1.0:
        return 1.0
    return sim


def sort_retrieval_hits(
    scored: list[tuple[VectorQueryHit, float]],
) -> list[tuple[VectorQueryHit, float]]:
    return sorted(
        scored,
        key=lambda row: (-row[1], str(row[0].document_id), row[0].chunk_index),
    )
