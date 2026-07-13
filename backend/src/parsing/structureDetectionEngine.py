"""Stateless engine for identifying document structural elements using heuristics."""

import re

from src.documents.canonical import (
    BlockMetadata,
    BlockType,
    CanonicalDocument,
)

RE_MD_HEADING = re.compile(r"^\s*#+\s+(.+)$")
RE_NUMBERED_HEADING = re.compile(r"^\s*\d+(\.\d+)*\s+[A-Z\d].*$")
RE_NAMED_HEADING = re.compile(
    r"^\s*(Chapter|Section|Appendix)\s+\d*[A-Z]?[:\-\s].*$", re.IGNORECASE
)
RE_BULLET_LIST = re.compile(r"^\s*[-*+•]\s+(.+)$", re.MULTILINE)
RE_NUMBERED_LIST = re.compile(r"^\s*\d+[\.\)]\s+(.+)$", re.MULTILINE)
RE_QUOTE = re.compile(r"^\s*>\s+(.+)$")
RE_CAPTION = re.compile(
    r"^\s*(Figure|Table|Fig\.|Image|Illustration)\s+\d+(\.\d+)*[:\-\s].*$", re.IGNORECASE
)
RE_TABLE_DIVIDER = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|?\s*:?-+:?\s*)*\|?\s*$")


class StructureDetectionEngine:
    """Classify document structural blocks using regular expressions and heuristics."""

    def detect(self, document: CanonicalDocument) -> CanonicalDocument:
        """Analyze a CanonicalDocument and update block classifications."""
        updated_blocks = []
        for block in document.blocks:
            detected_type, confidence = self._classify_block(block.content)

            original_metadata = block.metadata or BlockMetadata(page_number=1)
            extra_metadata = dict(original_metadata.extra_metadata or {})
            extra_metadata["structure_confidence"] = confidence

            updated_metadata = original_metadata.model_copy(
                update={"extra_metadata": extra_metadata}
            )
            updated_block = block.model_copy(
                update={
                    "type": detected_type,
                    "metadata": updated_metadata,
                }
            )
            updated_blocks.append(updated_block)

        return document.model_copy(update={"blocks": updated_blocks})

    def _classify_block(self, content: str) -> tuple[BlockType, float]:
        """Classify a single text string into a BlockType based on heuristics."""
        stripped = content.strip()
        if not stripped:
            return BlockType.UNKNOWN, 1.0

        if stripped.startswith("```") or stripped.endswith("```"):
            return BlockType.CODE, 1.0

        lines = [line.strip() for line in stripped.splitlines() if line.strip()]
        if len(lines) >= 2:
            has_divider = any(RE_TABLE_DIVIDER.match(line) for line in lines)
            has_pipes = any("|" in line for line in lines)
            if has_divider or (has_pipes and len(lines) >= 3):
                return BlockType.TABLE, 0.95

        if RE_BULLET_LIST.match(stripped) or RE_NUMBERED_LIST.match(stripped):
            return BlockType.LIST, 0.90

        if RE_QUOTE.match(stripped):
            return BlockType.QUOTE, 0.95

        if RE_CAPTION.match(stripped) and len(stripped) < 250:
            return BlockType.CAPTION, 0.90

        if RE_MD_HEADING.match(stripped):
            return BlockType.HEADING, 0.95

        if len(stripped) < 150 and not stripped.endswith("."):
            if RE_NUMBERED_HEADING.match(stripped) or RE_NAMED_HEADING.match(stripped):
                return BlockType.HEADING, 0.90

        return BlockType.PARAGRAPH, 1.0
