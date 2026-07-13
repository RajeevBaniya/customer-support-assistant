"""SQLAlchemy ORM model for parser and ingestion execution run metrics."""

from uuid import UUID

from sqlalchemy import Float, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.models.baseModel import BaseRow


class IngestionMetadata(BaseRow):
    """ORM representation of parser and ingestion metrics details."""

    __tablename__ = "document_ingestion_metadata"

    document_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    parser_name: Mapped[str] = mapped_column(String(64), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    fallback_usage_count: Mapped[int] = mapped_column(Integer, nullable=False)
    overlap_usage_count: Mapped[int] = mapped_column(Integer, nullable=False)
    parsing_duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    chunking_duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    mapping_duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
