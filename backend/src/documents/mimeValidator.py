from pathlib import Path

from src.shared.customExceptions import ValidationException

_ALLOWED_EXT_TO_MIMES: dict[str, tuple[str, ...]] = {
    ".pdf": ("application/pdf",),
    ".docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document",),
    ".txt": ("text/plain",),
    ".md": ("text/markdown", "text/x-markdown"),
}


def _suffix_lower(name: str) -> str:
    return Path(name).suffix.lower()


def _declared_matches_ext(ext: str, declared: str | None) -> bool:
    if not declared or not declared.strip():
        return False
    normalized = declared.split(";", 1)[0].strip().lower()
    allowed = _ALLOWED_EXT_TO_MIMES.get(ext)
    if not allowed:
        return False
    return normalized in {m.lower() for m in allowed}


def _sniff_matches_ext(ext: str, data: bytes) -> bool:
    if ext == ".pdf":
        return len(data) >= 5 and data[:5] == b"%PDF-"
    if ext == ".docx":
        return len(data) >= 4 and data[:2] == b"PK"
    if ext in {".txt", ".md"}:
        if not data:
            return True
        try:
            data[:4096].decode("utf-8")
        except UnicodeDecodeError:
            return False
        return True
    return False


def validate_document_upload(
    *,
    original_file_name: str,
    declared_content_type: str | None,
    file_bytes: bytes,
) -> tuple[str, str]:
    ext = _suffix_lower(original_file_name)
    if ext not in _ALLOWED_EXT_TO_MIMES:
        raise ValidationException(
            "Unsupported file type",
            details={"extension": ext or "(none)"},
        )
    if not _declared_matches_ext(ext, declared_content_type):
        raise ValidationException(
            "Declared content type does not match file extension",
            details={"extension": ext, "declared": declared_content_type},
        )
    if not _sniff_matches_ext(ext, file_bytes):
        raise ValidationException(
            "File content does not match extension",
            details={"extension": ext},
        )
    allowed = _ALLOWED_EXT_TO_MIMES[ext]
    declared_raw = (declared_content_type or "").split(";", 1)[0].strip().lower()
    for mime in allowed:
        if mime.lower() == declared_raw:
            return ext, mime
    return ext, allowed[0]
