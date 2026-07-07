"""Defines the BlockType enumeration representing the structural type of a document block."""

from enum import Enum


class BlockType(str, Enum):
    """Enumeration representing the semantic or structural category of a document block.

    This classification allows downstream layout processing and chunking to treat
    different sections (like tables or headers) with specialized rules.
    """

    PARAGRAPH = "paragraph"
    HEADING = "heading"
    TABLE = "table"
    CODE = "code"
    LIST = "list"
    QUOTE = "quote"
    CAPTION = "caption"
    UNKNOWN = "unknown"
