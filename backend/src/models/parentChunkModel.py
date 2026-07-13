"""SQLAlchemy ORM model for parent document chunks."""

from uuid import UUID

from sqlalchemy import ForeignKey, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.baseModel import BaseRow


class ParentChunk(BaseRow):
    """ORM representation of a parent document chunk.

    Stores layout-level document blocks joined together with full metadata.
    """

    __tablename__ = "document_parent_chunks"

    document_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    block_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    block_types: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    page_numbers: Mapped[list[int]] = mapped_column(JSONB, nullable=False)
    source_orders: Mapped[list[int]] = mapped_column(JSONB, nullable=False)
    hierarchy_levels: Mapped[list[int]] = mapped_column(JSONB, nullable=False)
    parser_confidence: Mapped[list[float]] = mapped_column(JSONB, nullable=False)
    structure_confidence: Mapped[list[float]] = mapped_column(JSONB, nullable=False)
