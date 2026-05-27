from io import BytesIO

from docx import Document


def extract_text(data: bytes) -> str:
    try:
        doc = Document(BytesIO(data))
    except Exception:
        return ""
    lines: list[str] = []
    for para in doc.paragraphs:
        t = (para.text or "").strip()
        if t:
            lines.append(t)
    return "\n".join(lines)
