"""Parser registry managing mapping and health checks for document parsers."""

from collections.abc import Callable

from src.parsing.baseParser import BaseParser
from src.parsing.docxParser import DocxParser
from src.parsing.markdownParser import MarkdownParser
from src.parsing.pdfParser import PdfParser
from src.parsing.textParser import TextParser

MIME_TO_PARSER_KEY: dict[str, str] = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "text",
    "text/markdown": "markdown",
    "text/x-markdown": "markdown",
}

_PARSERS: dict[str, BaseParser] = {
    "pdf": PdfParser(),
    "docx": DocxParser(),
    "text": TextParser(),
    "markdown": MarkdownParser(),
}


def parser_key_for_mime(mime_type: str) -> str | None:
    """Return parser key identifier associated with a MIME type."""
    base = (mime_type or "").split(";", 1)[0].strip().lower()
    return MIME_TO_PARSER_KEY.get(base)


def supported_mime_types() -> list[str]:
    """Return sorted list of all supported MIME types."""
    return sorted(MIME_TO_PARSER_KEY.keys())


def probe_imports() -> dict[str, bool]:
    """Inspect environment to check if third-party parser libraries are installed."""
    status_map: dict[str, bool] = {}
    try:
        import pypdf  # noqa: F401

        status_map["pdf"] = True
    except ImportError:
        status_map["pdf"] = False
    try:
        import docx  # noqa: F401

        status_map["docx"] = True
    except ImportError:
        status_map["docx"] = False
    status_map["text"] = True
    try:
        import bs4  # noqa: F401
        import markdown  # noqa: F401

        status_map["markdown"] = True
    except ImportError:
        status_map["markdown"] = False
    return status_map


def parsing_health() -> dict[str, object]:
    """Gather health and readiness status of parsing libraries."""
    import_flags = probe_imports()
    is_ready = (
        import_flags.get("pdf")
        and import_flags.get("docx")
        and import_flags.get("markdown")
        and import_flags.get("text", True)
    )
    return {
        "supported_mime_types": supported_mime_types(),
        "parsers": import_flags,
        "ready": bool(is_ready),
    }


def parser_for_mime(mime_type: str) -> BaseParser | None:
    """Retrieve parser instance associated with a MIME type."""
    key = parser_key_for_mime(mime_type)
    if key is None:
        return None
    return _PARSERS.get(key)


def parser_callable_for_mime(mime_type: str) -> Callable[[bytes], str] | None:
    """Legacy backward compatibility method."""
    parser = parser_for_mime(mime_type)
    if parser is None:
        return None

    from uuid import uuid4

    def _extract(data: bytes) -> str:
        document = parser.parse(data, uuid4())
        return "\n\n".join(block.content for block in document.blocks)

    return _extract
