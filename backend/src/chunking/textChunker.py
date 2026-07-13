import re


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace by collapsing excessive empty lines and carriage returns."""
    cleaned_text = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned_text = re.sub(r"[ \t]+\n", "\n", cleaned_text)
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)
    return cleaned_text.strip()


def chunk_with_offsets(
    text: str,
    *,
    chunk_size: int = 1200,
    overlap: int = 150,
) -> tuple[list[str], list[int]]:
    """Slice text into overlapping chunks using whitespace heuristic boundaries."""
    normalized_text = normalize_whitespace(text)
    if not normalized_text:
        return [], []
    chunks: list[str] = []
    start_indices: list[int] = []
    current_index = 0
    total_length = len(normalized_text)
    while current_index < total_length:
        end_index = min(current_index + chunk_size, total_length)
        if end_index <= current_index:
            end_index = min(current_index + 1, total_length)
        if end_index < total_length:
            search_back_range = min(80, end_index - current_index)
            split_index = normalized_text.rfind("\n\n", current_index + 1, end_index)
            if split_index == -1 or split_index < current_index + chunk_size // 2:
                split_index = normalized_text.rfind("\n", current_index + 1, end_index)
            if split_index != -1 and split_index > current_index + chunk_size // 3:
                end_index = min(split_index + 2, total_length)
            else:
                split_index = normalized_text.rfind(" ", end_index - search_back_range, end_index)
                if split_index != -1 and split_index > current_index:
                    end_index = split_index + 1
        chunk_text = normalized_text[current_index:end_index].strip()
        if chunk_text:
            chunks.append(chunk_text)
            start_indices.append(current_index)
        if end_index >= total_length:
            break
        step_size = max(1, end_index - current_index - overlap)
        current_index += step_size
    return chunks, start_indices


def page_for_chunk_start(
    start: int,
    page_for_char: list[int | None] | None,
) -> int | None:
    """Determine page number mapping for a specific text start offset."""
    if not page_for_char or start < 0 or start >= len(page_for_char):
        return None
    return page_for_char[start]
