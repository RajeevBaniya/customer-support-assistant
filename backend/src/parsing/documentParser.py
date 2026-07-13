"""Coordinates document parsing execution and exposes the backward compatibility layer."""

import asyncio
from dataclasses import dataclass
from time import perf_counter
from uuid import uuid4

from src.documents.canonical import CanonicalDocument
from src.observability.structuredLogger import get_logger
from src.parsing import parserRegistry

logger = get_logger("parsing.orchestration")

MAX_EXTRACTED_UTF8_BYTES = 5 * 1024 * 1024


@dataclass(frozen=True)
class ParsedPayload:
    """Extracted document payload for backward compatibility."""

    text: str
    parser_key: str
    page_for_char: list[int | None] | None


def assert_extracted_size(text: str) -> None:
    """Assert that the extracted text size does not exceed the allowed limit."""
    if len(text.encode("utf-8")) > MAX_EXTRACTED_UTF8_BYTES:
        raise ValueError("extracted_text_too_large")


async def parse_to_canonical(*, mime_type: str, data: bytes) -> CanonicalDocument:
    """Parse raw document bytes and run structure detection, yielding a CanonicalDocument."""
    parser_key = parserRegistry.parser_key_for_mime(mime_type)
    if parser_key is None:
        raise ValueError("unsupported_mime_for_parsing")

    parser = parserRegistry.parser_for_mime(mime_type)
    if parser is None:
        raise ValueError("parser_missing")

    start_time = perf_counter()
    success = False
    block_count = 0
    parser_version = "unknown"

    try:

        def _run() -> CanonicalDocument:
            return parser.parse(data, uuid4())

        document = await asyncio.to_thread(_run)

        if not isinstance(document, CanonicalDocument):
            raise TypeError("Parser did not return a CanonicalDocument")

        parser_version = document.metadata.parser_version
        block_count = len(document.blocks)

        detection_start_time = perf_counter()
        from src.parsing.structureDetectionEngine import StructureDetectionEngine

        engine = StructureDetectionEngine()
        document = engine.detect(document)
        detection_duration = perf_counter() - detection_start_time

        type_dist: dict[str, int] = {}
        conf_dist: list[float] = []
        for block in document.blocks:
            type_dist[block.type.value] = type_dist.get(block.type.value, 0) + 1
            confidence = 1.0
            if block.metadata and block.metadata.extra_metadata:
                confidence_value = block.metadata.extra_metadata.get("structure_confidence", 1.0)
                if isinstance(confidence_value, int | float):
                    confidence = float(confidence_value)
            conf_dist.append(confidence)

        mean_confidence = sum(conf_dist) / len(conf_dist) if conf_dist else 1.0

        logger.info(
            "structure_detection_completed",
            detection_duration_seconds=round(detection_duration, 4),
            block_count=len(document.blocks),
            block_type_distribution=type_dist,
            mean_structure_confidence=round(mean_confidence, 4),
        )
        success = True
        return document

    except Exception as exception:
        logger.error(
            "parsing_failed",
            parser_selected=parser.__class__.__name__,
            parser_version=parser_version,
            success=False,
            error=str(exception),
        )
        raise
    finally:
        duration_seconds = perf_counter() - start_time
        logger.info(
            "parsing_completed",
            parser_selected=parser.__class__.__name__,
            parser_version=parser_version,
            parsing_duration_seconds=round(duration_seconds, 4),
            success=success,
            block_count=block_count,
        )


async def parse_uploaded_bytes(*, mime_type: str, data: bytes) -> ParsedPayload:
    """Parse document bytes and return legacy ParsedPayload for compatibility."""
    parser_key = parserRegistry.parser_key_for_mime(mime_type)
    if parser_key is None:
        raise ValueError("unsupported_mime_for_parsing")

    document = await parse_to_canonical(mime_type=mime_type, data=data)

    text_parts = []
    page_for_char = []
    for index, block in enumerate(document.blocks):
        if index > 0:
            text_parts.append("\n\n")
            last_page = document.blocks[index - 1].metadata.page_number
            page_for_char.extend([last_page] * 2)

        text_parts.append(block.content)
        page_for_char.extend([block.metadata.page_number] * len(block.content))

    text = "".join(text_parts)
    assert_extracted_size(text)

    return ParsedPayload(text=text, parser_key=parser_key, page_for_char=page_for_char)
