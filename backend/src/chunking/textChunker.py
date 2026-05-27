import re


def normalize_whitespace(text: str) -> str:
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def chunk_with_offsets(
    text: str,
    *,
    chunk_size: int = 1200,
    overlap: int = 150,
) -> tuple[list[str], list[int]]:
    base = normalize_whitespace(text)
    if not base:
        return [], []
    chunks: list[str] = []
    starts: list[int] = []
    i = 0
    n = len(base)
    while i < n:
        end = min(i + chunk_size, n)
        if end <= i:
            end = min(i + 1, n)
        if end < n:
            back = min(80, end - i)
            cut = base.rfind("\n\n", i + 1, end)
            if cut == -1 or cut < i + chunk_size // 2:
                cut = base.rfind("\n", i + 1, end)
            if cut != -1 and cut > i + chunk_size // 3:
                end = min(cut + 2, n)
            else:
                cut = base.rfind(" ", end - back, end)
                if cut != -1 and cut > i:
                    end = cut + 1
        piece = base[i:end].strip()
        if piece:
            chunks.append(piece)
            starts.append(i)
        if end >= n:
            break
        step = max(1, end - i - overlap)
        i += step
    return chunks, starts


def page_for_chunk_start(
    start: int,
    page_for_char: list[int | None] | None,
) -> int | None:
    if not page_for_char or start < 0 or start >= len(page_for_char):
        return None
    return page_for_char[start]
