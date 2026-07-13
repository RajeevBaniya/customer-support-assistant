"""Shared text processing utilities and helpers."""

import re

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def split_sentences(text: str) -> list[str]:
    """Split text into sentences deterministically, trimming whitespaces."""
    if not text:
        return []
    return [sentence.strip() for sentence in _SENT_SPLIT.split(text) if sentence.strip()]
