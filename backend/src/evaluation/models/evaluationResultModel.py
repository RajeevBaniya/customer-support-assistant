from __future__ import annotations

from uuid import UUID

from sqlalchemy import Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.baseModel import BaseRow


class EvaluationResult(BaseRow):
    __tablename__ = "evaluation_results"

    run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("evaluation_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    conversation_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_context: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_chunk_refs: Mapped[list[object]] = mapped_column(JSONB, nullable=False)
    citations: Mapped[list[object]] = mapped_column(JSONB, nullable=False)
    hallucination_score: Mapped[float] = mapped_column(Float, nullable=False)
    faithfulness_score: Mapped[float] = mapped_column(Float, nullable=False)
    retrieval_relevance_score: Mapped[float] = mapped_column(Float, nullable=False)
    answer_relevance_score: Mapped[float] = mapped_column(Float, nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    dataset_row_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
