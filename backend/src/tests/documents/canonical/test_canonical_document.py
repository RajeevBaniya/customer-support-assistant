"""Unit tests for CanonicalDocument validation, structures, and extension points."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.documents.canonical import (
    BlockMetadata,
    BlockType,
    CanonicalDocument,
    DocumentBlock,
    DocumentMetadata,
)


def test_block_types_defined() -> None:
    """Verifies that the required canonical structural block types are supported."""
    assert BlockType.HEADING.value == "heading"
    assert BlockType.PARAGRAPH.value == "paragraph"
    assert BlockType.TABLE.value == "table"
    assert BlockType.CODE.value == "code"
    assert BlockType.LIST.value == "list"
    assert BlockType.QUOTE.value == "quote"
    assert BlockType.CAPTION.value == "caption"
    assert BlockType.UNKNOWN.value == "unknown"


def test_block_type_fallback() -> None:
    """Verifies that unrecognized block type strings fallback gracefully to BlockType.UNKNOWN."""
    block = DocumentBlock(
        id="block-1",
        type="nonexistent-type",  # type: ignore[arg-type]
        content="some text",
        index=0,
    )
    assert block.type == BlockType.UNKNOWN


def test_immutability() -> None:
    """Verifies that models are frozen and raise errors on mutation attempt."""
    metadata = DocumentMetadata(
        parser_name="pypdf",
        parser_version="1.0.0",
    )
    with pytest.raises(ValidationError):
        # Modifying attributes on frozen models raises ValidationError.
        metadata.parser_name = "new-parser"


def test_canonical_document_valid() -> None:
    """Verifies that a well-formed CanonicalDocument validates successfully."""
    doc_id = uuid4()
    doc_meta = DocumentMetadata(
        author="Author",
        created_at=datetime.now(UTC),
        schema_version="1.0.0",
        parser_name="pypdf",
        parser_version="1.0.0",
        extra_metadata={"key": "val"},
    )
    block_meta = BlockMetadata(
        page_number=1,
        coordinates=[0.0, 10.0, 100.0, 200.0],
        extra_metadata={"font": "Arial"},
    )
    block1 = DocumentBlock(
        id="b1",
        type=BlockType.HEADING,
        content="Heading 1",
        parser_confidence=0.98,
        parent_id=None,
        hierarchy_level=0,
        source_order=1,
        index=0,
        metadata=block_meta,
    )
    block2 = DocumentBlock(
        id="b2",
        type=BlockType.PARAGRAPH,
        content="Paragraph text.",
        parser_confidence=1.0,
        parent_id="b1",
        hierarchy_level=1,
        source_order=2,
        index=1,
    )
    doc = CanonicalDocument(
        document_id=doc_id,
        metadata=doc_meta,
        blocks=[block1, block2],
    )
    assert doc.document_id == doc_id
    assert len(doc.blocks) == 2
    assert doc.blocks[0].id == "b1"
    assert doc.blocks[1].parent_id == "b1"


def test_canonical_document_duplicate_ids() -> None:
    """Verifies that duplicate block IDs raise a validation error."""
    doc_meta = DocumentMetadata(parser_name="pypdf", parser_version="1.0.0")
    block1 = DocumentBlock(id="b1", content="Text 1", index=0, source_order=0)
    block2 = DocumentBlock(id="b1", content="Text 2", index=1, source_order=1)
    with pytest.raises(ValidationError, match="Duplicate block ID detected"):
        CanonicalDocument(
            document_id=uuid4(),
            metadata=doc_meta,
            blocks=[block1, block2],
        )


def test_canonical_document_orphan_parent() -> None:
    """Verifies that an orphan parent block ID reference raises a validation error."""
    doc_meta = DocumentMetadata(parser_name="pypdf", parser_version="1.0.0")
    block1 = DocumentBlock(id="b1", content="Text 1", parent_id="nonexistent", index=0)
    with pytest.raises(ValidationError, match="Orphan block detected"):
        CanonicalDocument(
            document_id=uuid4(),
            metadata=doc_meta,
            blocks=[block1],
        )


def test_canonical_document_out_of_order() -> None:
    """Verifies that block lists not sorted by index raise a validation error."""
    doc_meta = DocumentMetadata(parser_name="pypdf", parser_version="1.0.0")
    block1 = DocumentBlock(id="b1", content="Text 1", index=1, source_order=0)
    block2 = DocumentBlock(id="b2", content="Text 2", index=0, source_order=1)
    with pytest.raises(ValidationError, match="Blocks list must be sorted"):
        CanonicalDocument(
            document_id=uuid4(),
            metadata=doc_meta,
            blocks=[block1, block2],
        )


def test_canonical_document_duplicate_source_order() -> None:
    """Verifies that duplicate source_order values raise a validation error."""
    doc_meta = DocumentMetadata(parser_name="pypdf", parser_version="1.0.0")
    block1 = DocumentBlock(id="b1", content="Text 1", index=0, source_order=1)
    block2 = DocumentBlock(id="b2", content="Text 2", index=1, source_order=1)
    with pytest.raises(ValidationError, match="Duplicate source_order detected"):
        CanonicalDocument(
            document_id=uuid4(),
            metadata=doc_meta,
            blocks=[block1, block2],
        )


def test_canonical_document_negative_fields() -> None:
    """Verifies that negative hierarchy_level or source_order raises a validation error."""
    with pytest.raises(ValidationError):
        # Validation on instantiation via standard constraints ge=0
        DocumentBlock(id="b1", content="Text 1", index=0, source_order=-1)
    with pytest.raises(ValidationError):
        # Validation on instantiation via standard constraints ge=0
        DocumentBlock(id="b2", content="Text 2", index=0, hierarchy_level=-1)


def test_canonical_document_empty_content() -> None:
    """Verifies that empty content for non-UNKNOWN types raises a validation error."""
    doc_meta = DocumentMetadata(parser_name="pypdf", parser_version="1.0.0")
    # Empty content for a known type (e.g. PARAGRAPH) must fail
    block1 = DocumentBlock(id="b1", type=BlockType.PARAGRAPH, content="", index=0)
    with pytest.raises(ValidationError, match="Empty content not allowed"):
        CanonicalDocument(
            document_id=uuid4(),
            metadata=doc_meta,
            blocks=[block1],
        )
    # Empty content for UNKNOWN must pass
    block2 = DocumentBlock(id="b2", type=BlockType.UNKNOWN, content="", index=0)
    doc = CanonicalDocument(
        document_id=uuid4(),
        metadata=doc_meta,
        blocks=[block2],
    )
    assert len(doc.blocks) == 1


def test_serialization_roundtrip() -> None:
    """Verifies that CanonicalDocument serializes and deserializes properly."""
    doc_id = uuid4()
    doc = CanonicalDocument(
        document_id=doc_id,
        metadata=DocumentMetadata(parser_name="pypdf", parser_version="1.0.0"),
        blocks=[DocumentBlock(id="b1", content="Text 1", index=0)],
    )
    serialized = doc.model_dump_json()
    deserialized = CanonicalDocument.model_validate_json(serialized)
    assert deserialized.document_id == doc_id
    assert len(deserialized.blocks) == 1
    assert deserialized.blocks[0].content == "Text 1"
