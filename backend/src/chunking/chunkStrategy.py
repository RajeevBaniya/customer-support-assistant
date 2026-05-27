from src.chunking.textChunker import chunk_with_offsets

DEFAULT_CHUNK = 1200
DEFAULT_OVERLAP = 150


def chunk_plain_text(text: str) -> tuple[list[str], list[int]]:
    return chunk_with_offsets(text, chunk_size=DEFAULT_CHUNK, overlap=DEFAULT_OVERLAP)
