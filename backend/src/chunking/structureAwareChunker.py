from src.chunking.docChunk import DocChunk
from src.documents.canonical import (
    BlockType,
    CanonicalDocument,
    DocumentBlock,
)
from src.shared.textHelpers import split_sentences

BLOCK_SEPARATOR_LEN = 2  # Length of "\n\n" separator when joining blocks


class StructureAwareChunker:
    """Engine responsible for grouping and splitting CanonicalDocument blocks."""

    def __init__(self, chunk_size: int = 1200, overlap: int = 150):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.fallback_count = 0
        self.overlap_count = 0

    def chunk(self, document: CanonicalDocument) -> list[DocChunk]:
        """Groups CanonicalDocument blocks into structured DocChunk instances."""
        if not document.blocks:
            return []

        chunks: list[DocChunk] = []
        current_blocks: list[DocumentBlock] = []

        for block in document.blocks:
            block_length = len(block.content)
            if not current_blocks:
                if block_length > self.chunk_size:
                    chunks.extend(self._split_single_block(block, document))
                else:
                    current_blocks.append(block)
                continue

            current_size = sum(len(b.content) for b in current_blocks) + BLOCK_SEPARATOR_LEN * (
                len(current_blocks) - 1
            )
            updated_size = current_size + BLOCK_SEPARATOR_LEN + block_length

            if updated_size <= self.chunk_size:
                current_blocks.append(block)
            else:
                chunks.append(self._build_chunk(current_blocks, document))
                current_blocks = self._get_overlap_blocks(current_blocks)

                if block_length > self.chunk_size:
                    chunks.extend(self._split_single_block(block, document))
                    current_blocks = []
                else:
                    current_blocks.append(block)

        if current_blocks:
            chunks.append(self._build_chunk(current_blocks, document))

        return chunks

    def _split_single_block(
        self, block: DocumentBlock, document: CanonicalDocument
    ) -> list[DocChunk]:
        """Splits a single block that exceeds chunk_size limit."""
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
            part_length = len(part)
            if not current_parts:
                if part_length > self.chunk_size:
                    part_slices = [
                        part[char_index : char_index + self.chunk_size]
                        for char_index in range(0, part_length, self.chunk_size)
                    ]
                    for slice_text in part_slices:
                        chunks.append(self._build_chunk_from_text(slice_text, block, document))
                else:
                    current_parts.append(part)
                continue

            current_size = sum(len(p) for p in current_parts) + len(
                join_char
            ) * (len(current_parts) - 1)
            if current_size + len(join_char) + part_length <= self.chunk_size:
                current_parts.append(part)
            else:
                text_content = join_char.join(current_parts)
                chunks.append(self._build_chunk_from_text(text_content, block, document))

                previous_part = current_parts[-1]
                if len(previous_part) <= self.overlap:
                    current_parts = [previous_part, part]
                else:
                    current_parts = [part]

        if current_parts:
            text_content = join_char.join(current_parts)
            chunks.append(self._build_chunk_from_text(text_content, block, document))

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

    def _build_chunk(
        self, blocks: list[DocumentBlock], document: CanonicalDocument
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
        )

    def _build_chunk_from_text(
        self, text: str, block: DocumentBlock, document: CanonicalDocument
    ) -> DocChunk:
        """Assembles a DocChunk from a single block's sliced text content."""
        page_no = block.metadata.page_number if block.metadata else None
        page_number = page_no if page_no is not None else 1

        structure_confidence = 1.0
        if block.metadata and block.metadata.extra_metadata:
            confidence_val = block.metadata.extra_metadata.get("structure_confidence", 1.0)
            if isinstance(confidence_val, int | float):
                structure_confidence = float(confidence_val)

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
        )
