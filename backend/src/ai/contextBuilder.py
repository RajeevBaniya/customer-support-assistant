import re
from dataclasses import dataclass

from src.schemas.retrievalSchemas import RetrievalChunkItem

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class ContextTextResult:
    text: str
    truncated: bool
    duplicate_sentences_removed: int
    input_char_len: int
    output_char_len: int


def _collapse_duplicate_sentences(block: str) -> tuple[str, int]:
    raw = block.strip()
    if not raw:
        return "", 0
    pieces = [p.strip() for p in _SENT_SPLIT.split(raw) if p.strip()]
    if len(pieces) <= 1:
        return raw, 0
    seen: set[str] = set()
    kept: list[str] = []
    removed = 0
    for s in pieces:
        if len(s) < 10:
            kept.append(s)
            continue
        key = " ".join(s.lower().split())[:500]
        if key in seen:
            removed += 1
            continue
        seen.add(key)
        kept.append(s)
    return ". ".join(kept), removed


def build_context_text(
    items: list[RetrievalChunkItem],
    *,
    max_chars: int,
    max_tokens: int = 6000,
) -> ContextTextResult:
    dup_total = 0
    parts: list[str] = []
    raw_len = 0
    for idx, item in enumerate(items, start=1):
        page = "?" if item.source_page is None else str(item.source_page)
        header = f"[{idx}] {item.document_name} page={page} chunk={item.chunk_index}\n"
        body = item.text.strip()
        cleaned, removed = _collapse_duplicate_sentences(body)
        dup_total += removed
        segment = header + cleaned + "\n\n"
        raw_len += len(segment)
        parts.append(segment)
    text = "".join(parts).strip()

    import tiktoken

    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)

    truncated = False
    if len(tokens) > max_tokens:
        text = enc.decode(tokens[: max_tokens - 1]).rstrip() + "..."
        truncated = True

    if len(text) > max_chars:
        text = text[: max_chars - 3].rstrip() + "..."
        truncated = True

    return ContextTextResult(
        text=text,
        truncated=truncated,
        duplicate_sentences_removed=dup_total,
        input_char_len=raw_len,
        output_char_len=len(text),
    )
