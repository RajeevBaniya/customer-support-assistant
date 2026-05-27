from datetime import datetime
from typing import Any
from uuid import UUID


def chunk_vector_id(organization_id: UUID, document_id: UUID, chunk_index: int) -> str:
    return f"org:{organization_id}:doc:{document_id}:chunk:{chunk_index}"


def build_chunk_metadata(
    *,
    document_id: UUID,
    organization_id: UUID,
    chunk_index: int,
    parser_type: str | None,
    source_page: int | None,
    document_created_at: datetime,
) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "document_id": str(document_id),
        "organization_id": str(organization_id),
        "chunk_index": chunk_index,
        "parser_type": (parser_type or "")[:64],
        "uploaded_at": document_created_at.isoformat(),
    }
    if source_page is not None:
        meta["source_page"] = int(source_page)
    return meta
