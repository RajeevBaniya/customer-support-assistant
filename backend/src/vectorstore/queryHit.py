from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class VectorQueryHit:
    vector_id: str
    document_id: UUID
    chunk_index: int
    distance: float
    text: str
    metadata: dict[str, Any]
