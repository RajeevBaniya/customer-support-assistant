"""Metadata serialization and payload building utilities for vector stores."""

from datetime import datetime
from typing import Any
from uuid import UUID

from src.chunking.childChunk import ChildChunk
from src.chunking.docChunk import DocChunk


def chunk_vector_id(
    organization_id: UUID, document_id: UUID, chunk_index: int
) -> str:
    """Generate stable vector ID string for legacy chunk indexes."""
    return f"org:{organization_id}:doc:{document_id}:chunk:{chunk_index}"


def child_vector_id(
    organization_id: UUID, document_id: UUID, child_id: UUID
) -> str:
    """Generate stable vector ID string for structured child chunks."""
    return f"org:{organization_id}:doc:{document_id}:child:{child_id}"


def parent_vector_id(
    organization_id: UUID, document_id: UUID, parent_id: UUID
) -> str:
    """Generate stable vector ID string for structured parent chunks."""
    return f"org:{organization_id}:doc:{document_id}:parent:{parent_id}"


def build_chunk_metadata(
    *,
    document_id: UUID,
    organization_id: UUID,
    chunk_index: int,
    parser_type: str | None,
    source_page: int | None,
    document_created_at: datetime,
) -> dict[str, Any]:
    """Build metadata payload dictionary for legacy document chunks."""
    metadata: dict[str, Any] = {
        "document_id": str(document_id),
        "organization_id": str(organization_id),
        "chunk_index": chunk_index,
        "parser_type": (parser_type or "")[:64],
        "uploaded_at": document_created_at.isoformat(),
    }
    if source_page is not None:
        metadata["source_page"] = int(source_page)
    return metadata


def build_child_chunk_metadata(
    *,
    child: ChildChunk,
    organization_id: UUID,
    uploaded_at: datetime,
    filename: str | None = None,
    file_type: str | None = None,
) -> dict[str, Any]:
    """Build rich metadata payload dictionary representing a ChildChunk for Pinecone."""
    return {
        "document_id": str(child.document_id),
        "organization_id": str(organization_id),
        "workspace_id": str(organization_id),
        "parent_id": str(child.parent_id),
        "child_id": str(child.child_id),
        "block_ids": [str(block_id) for block_id in child.block_ids],
        "block_types": [str(block_type) for block_type in child.block_types],
        "page_numbers": [int(page_number) for page_number in child.page_numbers],
        "hierarchy_level": [int(level) for level in child.hierarchy_levels],
        "source_order": [int(order) for order in child.source_orders],
        "parser_version": str(child.parser_version),
        "schema_version": str(child.schema_version),
        "parser_confidence": [float(confidence) for confidence in child.parser_confidence],
        "structure_confidence": [
            float(confidence) for confidence in child.structure_confidence
        ],
        "uploaded_at": uploaded_at.isoformat(),
        "created_at": uploaded_at.isoformat(),
        "filename": filename or "",
        "file_type": file_type or "",
        "page_number": child.page_numbers[0] if child.page_numbers else 1,
        "section_title": child.section_title or "",
        "section_id": str(child.section_id) if child.section_id else "",
        "chunk_index": child.chunk_index,
        "chunk_hash": child.chunk_hash or "",
        "ingestion_version": child.ingestion_version or "1.0.0",
    }


def build_parent_chunk_vector_metadata(
    *,
    parent: DocChunk,
    organization_id: UUID,
    uploaded_at: datetime,
    filename: str | None = None,
    file_type: str | None = None,
) -> dict[str, Any]:
    """Build rich metadata payload dictionary representing a Parent DocChunk for Pinecone."""
    return {
        "document_id": str(parent.document_id),
        "organization_id": str(organization_id),
        "workspace_id": str(organization_id),
        "parent_id": str(parent.parent_id) if parent.parent_id else "",
        "block_ids": [str(block_id) for block_id in parent.block_ids],
        "block_types": [str(block_type) for block_type in parent.block_types],
        "page_numbers": [int(page_number) for page_number in parent.page_numbers],
        "hierarchy_level": [int(level) for level in parent.hierarchy_levels],
        "source_order": [int(order) for order in parent.source_orders],
        "parser_version": str(parent.parser_version),
        "schema_version": str(parent.schema_version),
        "parser_confidence": [float(confidence) for confidence in parent.parser_confidence],
        "structure_confidence": [
            float(confidence) for confidence in parent.structure_confidence
        ],
        "uploaded_at": uploaded_at.isoformat(),
        "created_at": uploaded_at.isoformat(),
        "filename": filename or "",
        "file_type": file_type or "",
        "page_number": parent.page_numbers[0] if parent.page_numbers else 1,
        "section_title": parent.section_title or "",
        "section_id": str(parent.section_id) if parent.section_id else "",
        "chunk_index": parent.chunk_index,
        "chunk_hash": parent.chunk_hash or "",
        "ingestion_version": parent.ingestion_version or "1.0.0",
    }
