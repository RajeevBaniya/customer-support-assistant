from uuid import UUID

from src.schemas.ragSchemas import CitationItem
from src.schemas.retrievalSchemas import RetrievalChunkItem


def citations_from_chunks(items: list[RetrievalChunkItem]) -> list[CitationItem]:
    seen: set[tuple[UUID, int]] = set()
    out: list[CitationItem] = []
    for it in items:
        key = (it.document_id, it.chunk_index)
        if key in seen:
            continue
        seen.add(key)
        out.append(
            CitationItem(
                document_id=it.document_id,
                document_name=it.document_name,
                source_page=it.source_page,
                chunk_index=it.chunk_index,
            )
        )
    return out
