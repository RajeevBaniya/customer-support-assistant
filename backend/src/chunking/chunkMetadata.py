from uuid import UUID

from src.chunking.textChunker import page_for_chunk_start
from src.schemas.chunkSchemas import ChunkPreviewItem


def chunk_pages_for_starts(
    starts: list[int],
    page_for_char: list[int | None] | None,
) -> list[int | None]:
    return [page_for_chunk_start(s, page_for_char) for s in starts]


def token_estimate(text: str) -> int:
    return max(1, len(text) // 4)


def build_previews(
    *,
    document_id: UUID,
    parser_key: str,
    chunks: list[str],
    starts: list[int],
    page_for_char: list[int | None] | None,
    max_chunks: int = 5,
    preview_len: int = 200,
) -> list[ChunkPreviewItem]:
    out: list[ChunkPreviewItem] = []
    for idx, (body, start) in enumerate(zip(chunks, starts, strict=True)):
        if idx >= max_chunks:
            break
        preview = body[:preview_len]
        sp = page_for_chunk_start(start, page_for_char)
        out.append(
            ChunkPreviewItem(
                chunk_index=idx,
                source_document_id=document_id,
                source_page=sp,
                character_count=len(body),
                token_estimate=token_estimate(body),
                parser_type=parser_key,
                preview_text=preview,
            )
        )
    return out
