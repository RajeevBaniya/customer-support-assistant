from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "add_document_parsing_columns"
down_revision: str | None = "add_documents_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column(
            "parsing_status",
            sa.String(length=32),
            server_default="pending",
            nullable=False,
        ),
    )
    op.add_column(
        "documents",
        sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("parser_type", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column(
            "chunk_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.alter_column("documents", "parsing_status", server_default=None)


def downgrade() -> None:
    op.drop_column("documents", "chunk_count")
    op.drop_column("documents", "parser_type")
    op.drop_column("documents", "parsed_at")
    op.drop_column("documents", "parsing_status")
