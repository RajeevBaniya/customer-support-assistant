from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError


def extract_text_and_page_map(data: bytes) -> tuple[str, list[int | None]]:
    try:
        reader = PdfReader(BytesIO(data), strict=False)
    except (PdfReadError, OSError, ValueError):
        return "", []
    text_parts: list[str] = []
    mapping: list[int | None] = []
    first = True
    for page_no, page in enumerate(reader.pages, start=1):
        if not first:
            text_parts.append("\n")
            mapping.append(None)
        first = False
        try:
            t = page.extract_text() or ""
        except Exception:
            t = ""
        text_parts.append(t)
        mapping.extend([page_no] * len(t))
    text = "".join(text_parts)
    if len(mapping) != len(text):
        return text, [None] * len(text)
    return text, mapping


def extract_text(data: bytes) -> str:
    return extract_text_and_page_map(data)[0]
