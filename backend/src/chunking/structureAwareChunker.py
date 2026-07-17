import hashlib
import re
from uuid import UUID, uuid4

from src.chunking.chunkMetadata import token_estimate
from src.chunking.docChunk import DocChunk
from src.documents.canonical import (
    BlockType,
    CanonicalDocument,
    DocumentBlock,
)
from src.shared.textHelpers import split_sentences

BLOCK_SEPARATOR_LEN = 2  # Length of "\n\n" separator when joining blocks


def calculate_normalized_hash(text: str) -> str:
    """Computes SHA-256 hash of normalized text for deterministic duplicate detection."""
    normalized = re.sub(r"\s+", " ", text).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class StructureAwareChunker:
    """Engine responsible for grouping and splitting CanonicalDocument blocks semantically."""

    def __init__(
        self,
        chunk_size: int = 1200,
        overlap: int = 150,
        max_tokens: int = 300,
        min_tokens: int = 25,
        ingestion_version: str = "1.0.0",
        workspace_id: UUID | None = None,
    ) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.max_tokens = max_tokens
        self.min_tokens = min_tokens
        self.ingestion_version = ingestion_version
        self.workspace_id = workspace_id
        self.fallback_count = 0
        self.overlap_count = 0

    def chunk(self, document: CanonicalDocument) -> list[DocChunk]:
        """Groups CanonicalDocument blocks into semantically aligned DocChunks."""
        if not document.blocks:
            return []

        chunks: list[DocChunk] = []
        current_blocks: list[DocumentBlock] = []

        current_section_id = uuid4()
        current_section_title = "Introduction"

        for block in document.blocks:
            if block.type == BlockType.HEADING:
                if current_blocks:
                    chunks.append(
                        self._build_semantic_chunk(
                            current_blocks,
                            document,
                            current_section_id,
                            current_section_title,
                            len(chunks),
                        )
                    )
                    current_blocks = []
                current_section_id = uuid4()
                current_section_title = block.content.strip()

            block_tokens = token_estimate(block.content)

            if not current_blocks:
                if block_tokens > self.max_tokens:
                    chunks.extend(
                        self._split_semantic_block(
                            block,
                            document,
                            current_section_id,
                            current_section_title,
                            len(chunks),
                        )
                    )
                else:
                    current_blocks.append(block)
                continue

            current_text = "\n\n".join(b.content for b in current_blocks)
            current_tokens = token_estimate(current_text)

            if current_tokens + block_tokens <= self.max_tokens:
                current_blocks.append(block)
            else:
                chunks.append(
                    self._build_semantic_chunk(
                        current_blocks,
                        document,
                        current_section_id,
                        current_section_title,
                        len(chunks),
                    )
                )
                current_blocks = self._get_overlap_blocks(current_blocks)

                if block_tokens > self.max_tokens:
                    chunks.extend(
                        self._split_semantic_block(
                            block,
                            document,
                            current_section_id,
                            current_section_title,
                            len(chunks),
                        )
                    )
                    current_blocks = []
                else:
                    current_blocks.append(block)

        if current_blocks:
            chunks.append(
                self._build_semantic_chunk(
                    current_blocks,
                    document,
                    current_section_id,
                    current_section_title,
                    len(chunks),
                )
            )

        return chunks

    def _split_semantic_block(
        self,
        block: DocumentBlock,
        document: CanonicalDocument,
        section_id: UUID,
        section_title: str,
        start_index: int,
    ) -> list[DocChunk]:
        """Splits a single block that exceeds max_tokens limit semantically."""
        self.fallback_count += 1
        if block.type in (BlockType.TABLE, BlockType.CODE, BlockType.LIST):
            parts = block.content.splitlines()
            join_char = "\n"
        else:
            parts = self._split_into_sentences(block.content)
            join_char = " "

        chunks: list[DocChunk] = []
        current_parts: list[str] = []

        for part in parts:
            part_tokens = token_estimate(part)
            if not current_parts:
                if part_tokens > self.max_tokens:
                    part_length = len(part)
                    char_chunk_size = self.max_tokens * 4
                    part_slices = [
                        part[char_index : char_index + char_chunk_size]
                        for char_index in range(0, part_length, char_chunk_size)
                    ]
                    for slice_text in part_slices:
                        chunks.append(
                            self._build_semantic_chunk_from_text(
                                slice_text,
                                block,
                                document,
                                section_id,
                                section_title,
                                start_index + len(chunks),
                            )
                        )
                else:
                    current_parts.append(part)
                continue

            current_text = join_char.join(current_parts)
            current_tokens = token_estimate(current_text)

            if current_tokens + token_estimate(join_char) + part_tokens <= self.max_tokens:
                current_parts.append(part)
            else:
                text_content = join_char.join(current_parts)
                chunks.append(
                    self._build_semantic_chunk_from_text(
                        text_content,
                        block,
                        document,
                        section_id,
                        section_title,
                        start_index + len(chunks),
                    )
                )

                previous_part = current_parts[-1]
                if len(previous_part) <= self.overlap:
                    current_parts = [previous_part, part]
                else:
                    current_parts = [part]

        if current_parts:
            text_content = join_char.join(current_parts)
            chunks.append(
                self._build_semantic_chunk_from_text(
                    text_content,
                    block,
                    document,
                    section_id,
                    section_title,
                    start_index + len(chunks),
                )
            )

        return chunks

    def _split_into_sentences(self, text: str) -> list[str]:
        """Splits text into sentences deterministically."""
        return split_sentences(text)

    def _get_overlap_blocks(self, blocks: list[DocumentBlock]) -> list[DocumentBlock]:
        """Identifies overlap sentence context to carry forward to the next chunk."""
        if not blocks or self.overlap <= 0:
            return []

        last_block = blocks[-1]
        last_length = len(last_block.content)
        if last_length <= self.overlap:
            self.overlap_count += 1
            return [last_block]

        sentences = self._split_into_sentences(last_block.content)
        accumulated: list[str] = []
        current_length = 0
        for sentence in reversed(sentences):
            if current_length + len(sentence) + 1 <= self.overlap:
                accumulated.insert(0, sentence)
                current_length += len(sentence) + 1
            else:
                break

        if accumulated:
            overlap_content = " ".join(accumulated)
            overlap_block = last_block.model_copy(
                update={
                    "id": f"{last_block.id}-overlap",
                    "content": overlap_content,
                }
            )
            self.overlap_count += 1
            return [overlap_block]

        return []

    def _build_semantic_chunk(
        self,
        blocks: list[DocumentBlock],
        document: CanonicalDocument,
        section_id: UUID,
        section_title: str,
        chunk_index: int,
    ) -> DocChunk:
        """Assembles a DocChunk from a list of grouped blocks."""
        text = "\n\n".join(block.content for block in blocks)
        block_ids = [block.id for block in blocks]
        block_types = [block.type.value for block in blocks]

        page_numbers = []
        for block in blocks:
            page_number = block.metadata.page_number if block.metadata else None
            page_numbers.append(page_number if page_number is not None else 1)

        source_orders = [block.source_order for block in blocks]
        hierarchy_levels = [block.hierarchy_level for block in blocks]
        parser_confidences = [block.parser_confidence for block in blocks]

        structure_confidences = []
        for block in blocks:
            confidence = 1.0
            if block.metadata and block.metadata.extra_metadata:
                confidence_val = block.metadata.extra_metadata.get("structure_confidence", 1.0)
                if isinstance(confidence_val, int | float):
                    confidence = float(confidence_val)
            structure_confidences.append(confidence)

        chunk_hash = calculate_normalized_hash(text)

        return DocChunk(
            text=text,
            document_id=document.document_id,
            block_ids=block_ids,
            block_types=block_types,
            page_numbers=page_numbers,
            source_orders=source_orders,
            hierarchy_levels=hierarchy_levels,
            parser_version=document.metadata.parser_version,
            schema_version=document.metadata.schema_version,
            parser_confidence=parser_confidences,
            structure_confidence=structure_confidences,
            section_id=section_id,
            section_title=section_title,
            chunk_index=chunk_index,
            chunk_hash=chunk_hash,
            ingestion_version=self.ingestion_version,
            workspace_id=self.workspace_id,
        )

    def _build_semantic_chunk_from_text(
        self,
        text: str,
        block: DocumentBlock,
        document: CanonicalDocument,
        section_id: UUID,
        section_title: str,
        chunk_index: int,
    ) -> DocChunk:
        """Assembles a DocChunk from a single block's sliced text content."""
        page_no = block.metadata.page_number if block.metadata else None
        page_number = page_no if page_no is not None else 1

        structure_confidence = 1.0
        if block.metadata and block.metadata.extra_metadata:
            confidence_val = block.metadata.extra_metadata.get("structure_confidence", 1.0)
            if isinstance(confidence_val, int | float):
                structure_confidence = float(confidence_val)

        chunk_hash = calculate_normalized_hash(text)

        return DocChunk(
            text=text,
            document_id=document.document_id,
            block_ids=[block.id],
            block_types=[block.type.value],
            page_numbers=[page_number],
            source_orders=[block.source_order],
            hierarchy_levels=[block.hierarchy_level],
            parser_version=document.metadata.parser_version,
            schema_version=document.metadata.schema_version,
            parser_confidence=[block.parser_confidence],
            structure_confidence=[structure_confidence],
            section_id=section_id,
            section_title=section_title,
            chunk_index=chunk_index,
            chunk_hash=chunk_hash,
            ingestion_version=self.ingestion_version,
            workspace_id=self.workspace_id,
        )
