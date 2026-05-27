from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "add_document_embedding_fields"
down_revision: str | None = "add_document_parsing_columns"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column(
            "embedding_status",
            sa.String(length=32),
            server_default="pending",
            nullable=False,
        ),
    )
    op.add_column(
        "documents",
        sa.Column("embedded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("embedding_model", sa.String(length=256), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column(
            "vector_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.execute(
        sa.text(
            "UPDATE documents SET embedding_status = 'skipped' "
            "WHERE parsing_status IS DISTINCT FROM 'parsed'"
        )
    )
    op.alter_column("documents", "embedding_status", server_default=None)


def downgrade() -> None:
    op.drop_column("documents", "vector_count")
    op.drop_column("documents", "embedding_model")
    op.drop_column("documents", "embedded_at")
    op.drop_column("documents", "embedding_status")
