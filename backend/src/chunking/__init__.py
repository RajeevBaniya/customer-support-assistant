"""Chunking package.

Exposes text chunking utilities and the Structure-aware Chunking Engine.
"""

from src.chunking.childChunk import ChildChunk
from src.chunking.docChunk import DocChunk
from src.chunking.parentChildBuilder import ParentChildBuilder
from src.chunking.structureAwareChunker import StructureAwareChunker

__all__ = [
    "ChildChunk",
    "DocChunk",
    "ParentChildBuilder",
    "StructureAwareChunker",
]
