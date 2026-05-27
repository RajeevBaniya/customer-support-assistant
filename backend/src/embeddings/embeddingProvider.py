from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingProvider(Protocol):
    async def encode_batch(self, texts: list[str]) -> list[list[float]]:
        """Return one L2-normalized dense vector per input text (same order, same length)."""
