import asyncio
from dataclasses import dataclass

from src.parsing import parserRegistry
from src.parsing.pdfParser import extract_text_and_page_map

MAX_EXTRACTED_UTF8_BYTES = 5 * 1024 * 1024


@dataclass(frozen=True)
class ParsedPayload:
    text: str
    parser_key: str
    page_for_char: list[int | None] | None


def assert_extracted_size(text: str) -> None:
    if len(text.encode("utf-8")) > MAX_EXTRACTED_UTF8_BYTES:
        raise ValueError("extracted_text_too_large")


async def parse_uploaded_bytes(*, mime_type: str, data: bytes) -> ParsedPayload:
    key = parserRegistry.parser_key_for_mime(mime_type)
    if key is None:
        raise ValueError("unsupported_mime_for_parsing")
    if key == "pdf":

        def _run() -> tuple[str, list[int | None]]:
            return extract_text_and_page_map(data)

        text, pmap = await asyncio.to_thread(_run)
        assert_extracted_size(text)
        return ParsedPayload(text=text, parser_key=key, page_for_char=pmap or None)
    fn = parserRegistry.parser_callable_for_mime(mime_type)
    if fn is None:
        raise ValueError("parser_missing")

    def _sync() -> str:
        return fn(data)

    text = await asyncio.to_thread(_sync)
    assert_extracted_size(text)
    return ParsedPayload(text=text, parser_key=key, page_for_char=None)
