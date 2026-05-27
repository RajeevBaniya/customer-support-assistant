from collections.abc import Callable

MIME_TO_PARSER_KEY: dict[str, str] = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "text",
    "text/markdown": "markdown",
    "text/x-markdown": "markdown",
}


def parser_key_for_mime(mime_type: str) -> str | None:
    base = (mime_type or "").split(";", 1)[0].strip().lower()
    return MIME_TO_PARSER_KEY.get(base)


def supported_mime_types() -> list[str]:
    return sorted(MIME_TO_PARSER_KEY.keys())


def probe_imports() -> dict[str, bool]:
    out: dict[str, bool] = {}
    try:
        import pypdf  # noqa: F401

        out["pdf"] = True
    except ImportError:
        out["pdf"] = False
    try:
        import docx  # noqa: F401

        out["docx"] = True
    except ImportError:
        out["docx"] = False
    out["text"] = True
    try:
        import bs4  # noqa: F401
        import markdown  # noqa: F401

        out["markdown"] = True
    except ImportError:
        out["markdown"] = False
    return out


def parsing_health() -> dict[str, object]:
    flags = probe_imports()
    ready = (
        flags.get("pdf") and flags.get("docx") and flags.get("markdown") and flags.get("text", True)
    )
    return {
        "supported_mime_types": supported_mime_types(),
        "parsers": flags,
        "ready": bool(ready),
    }


def parser_callable_for_mime(mime_type: str) -> Callable[[bytes], str] | None:
    key = parser_key_for_mime(mime_type)
    if key == "pdf":
        from src.parsing.pdfParser import extract_text as _fn

        return _fn
    if key == "docx":
        from src.parsing.docxParser import extract_text as _fn

        return _fn
    if key == "text":
        from src.parsing.textParser import extract_text as _fn

        return _fn
    if key == "markdown":
        from src.parsing.markdownParser import extract_text as _fn

        return _fn
    return None
