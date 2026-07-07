from src.chunking.textChunker import chunk_with_offsets

DEFAULT_CHUNK = 1200
DEFAULT_OVERLAP = 150


def chunk_plain_text(
    text: str,
    *,
    chunk_size: int = 1200,
    overlap: int = 150,
) -> tuple[list[str], list[int]]:
    return chunk_with_offsets(text, chunk_size=chunk_size, overlap=overlap)
