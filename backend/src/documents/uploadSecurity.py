from pathlib import Path

from src.shared.customExceptions import ValidationException

MAX_UPLOAD_BYTES = 25 * 1024 * 1024

_BLOCKED_SUFFIXES: frozenset[str] = frozenset(
    {
        ".exe",
        ".sh",
        ".bat",
        ".js",
        ".dll",
        ".cmd",
        ".ps1",
        ".scr",
        ".msi",
    }
)


def normalize_original_filename(raw: str | None) -> str:
    if raw is None or not str(raw).strip():
        raise ValidationException("Missing file name", details={"field": "filename"})
    raw_s = str(raw).strip()
    if ".." in raw_s or "/" in raw_s or "\\" in raw_s:
        raise ValidationException("Path segments are not allowed in file name")
    base = Path(raw_s).name.strip()
    if not base or base in {".", ".."}:
        raise ValidationException("Invalid file name", details={"field": "filename"})
    return base[:255]


def assert_extension_not_blocked(filename: str) -> None:
    lower = filename.lower()
    for blocked in _BLOCKED_SUFFIXES:
        if lower.endswith(blocked):
            raise ValidationException(
                "This file type is not allowed",
                details={"suffix": blocked},
            )


def assert_upload_size(file_size: int) -> None:
    if file_size > MAX_UPLOAD_BYTES:
        raise ValidationException(
            "File exceeds maximum upload size",
            details={"max_bytes": MAX_UPLOAD_BYTES, "file_size": file_size},
        )
