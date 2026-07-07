"""Canonical Document package.

Exposes the unified document layout models.
"""

from src.documents.canonical.block_metadata import BlockMetadata
from src.documents.canonical.block_type import BlockType
from src.documents.canonical.canonical_document import CanonicalDocument
from src.documents.canonical.document_block import DocumentBlock
from src.documents.canonical.document_metadata import DocumentMetadata

__all__ = [
    "BlockMetadata",
    "BlockType",
    "CanonicalDocument",
    "DocumentBlock",
    "DocumentMetadata",
]
