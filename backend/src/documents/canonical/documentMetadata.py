"""Defines the DocumentMetadata model representing global metadata for a canonical document."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentMetadata(BaseModel):
    """Global metadata for a CanonicalDocument.

    Contains information about the parser, schema version, and other metadata.
    All properties are immutable.
    """

    model_config = ConfigDict(frozen=True)

    author: str | None = Field(
        default=None,
        description="The author of the source document, if extracted.",
    )
    created_at: datetime | None = Field(
        default=None,
        description="The creation timestamp of the document, if extracted.",
    )
    schema_version: str = Field(
        default="1.0.0",
        description="The version of the canonical document schema used.",
    )
    parser_name: str = Field(
        ...,
        description="The name of the parser that processed the source document.",
    )
    parser_version: str = Field(
        ...,
        description="The version of the parser that processed the source document.",
    )
    extra_metadata: dict[str, object] = Field(
        default_factory=dict,
        description="A dictionary for parser-specific attributes and custom extensions.",
    )
