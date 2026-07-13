from uuid import UUID, uuid4

from src.chunking.childChunk import ChildChunk
from src.chunking.docChunk import DocChunk
from src.shared.textHelpers import split_sentences


class ParentChildBuilder:
    """Builder that partitions layout-level parent chunks into smaller child chunks."""

    def __init__(self, child_chunk_size: int = 400, child_chunk_overlap: int = 50):
        self.child_chunk_size = child_chunk_size
        self.child_chunk_overlap = child_chunk_overlap

    def build_relations(
        self, parents: list[DocChunk]
    ) -> tuple[list[DocChunk], list[ChildChunk]]:
        """Slices parents into sentence-aligned child chunks."""
        evolved_parents: list[DocChunk] = []
        all_children: list[ChildChunk] = []

        for parent in parents:
            parent_id = uuid4()
            child_chunks = self._generate_children(parent, parent_id)

            child_ids = [child.child_id for child in child_chunks]
            evolved = parent.model_copy(
                update={
                    "parent_id": parent_id,
                    "child_ids": child_ids,
                }
            )
            evolved_parents.append(evolved)
            all_children.extend(child_chunks)

        return evolved_parents, all_children

    def _generate_children(
        self, parent: DocChunk, parent_id: UUID
    ) -> list[ChildChunk]:
        """Slices the parent chunk text into children."""
        text = parent.text
        if len(text) <= self.child_chunk_size:
            child = ChildChunk(
                child_id=uuid4(),
                parent_id=parent_id,
                text=text,
                document_id=parent.document_id,
                block_ids=parent.block_ids,
                block_types=parent.block_types,
                page_numbers=parent.page_numbers,
                source_orders=parent.source_orders,
                hierarchy_levels=parent.hierarchy_levels,
                parser_version=parent.parser_version,
                schema_version=parent.schema_version,
                parser_confidence=parent.parser_confidence,
                structure_confidence=parent.structure_confidence,
            )
            return [child]

        sentences = split_sentences(text)
        if not sentences:
            sentences = [text]

        child_chunks: list[ChildChunk] = []
        current_sentences: list[str] = []

        for sentence in sentences:
            sentence_length = len(sentence)
            if not current_sentences:
                if sentence_length > self.child_chunk_size:
                    sentence_parts = [
                        sentence[char_index : char_index + self.child_chunk_size]
                        for char_index in range(0, sentence_length, self.child_chunk_size)
                    ]
                    for part_text in sentence_parts:
                        child_chunks.append(
                            self._build_child(part_text, parent, parent_id)
                        )
                else:
                    current_sentences.append(sentence)
                continue

            current_size = (
                sum(len(sentence_item) for sentence_item in current_sentences)
                + len(current_sentences)
                - 1
            )
            if current_size + 1 + sentence_length <= self.child_chunk_size:
                current_sentences.append(sentence)
            else:
                child_text = " ".join(current_sentences)
                child_chunks.append(
                    self._build_child(child_text, parent, parent_id)
                )

                overlap_sents: list[str] = []
                current_overlap_length = 0
                for overlap_sentence in reversed(current_sentences):
                    if (
                        current_overlap_length + len(overlap_sentence) + 1
                        <= self.child_chunk_overlap
                    ):
                        overlap_sents.insert(0, overlap_sentence)
                        current_overlap_length += len(overlap_sentence) + 1
                    else:
                        break
                current_sentences = overlap_sents + [sentence]

        if current_sentences:
            child_text = " ".join(current_sentences)
            child_chunks.append(
                self._build_child(child_text, parent, parent_id)
            )

        return child_chunks

    def _build_child(
        self, text: str, parent: DocChunk, parent_id: UUID
    ) -> ChildChunk:
        """Assemble a single ChildChunk instance from slices."""
        return ChildChunk(
            child_id=uuid4(),
            parent_id=parent_id,
            text=text,
            document_id=parent.document_id,
            block_ids=parent.block_ids,
            block_types=parent.block_types,
            page_numbers=parent.page_numbers,
            source_orders=parent.source_orders,
            hierarchy_levels=parent.hierarchy_levels,
            parser_version=parent.parser_version,
            schema_version=parent.schema_version,
            parser_confidence=parent.parser_confidence,
            structure_confidence=parent.structure_confidence,
        )
