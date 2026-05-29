from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GenerationUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated: bool


def estimate_token_count(text: str) -> int:
    stripped = text.strip()
    if not stripped:
        return 0
    return max(1, len(stripped) // 4)


def usage_from_provider_counts(
    *,
    prompt_tokens: int,
    completion_tokens: int,
) -> GenerationUsage:
    prompt = max(0, int(prompt_tokens))
    completion = max(0, int(completion_tokens))
    return GenerationUsage(
        prompt_tokens=prompt,
        completion_tokens=completion,
        total_tokens=prompt + completion,
        estimated=False,
    )


def usage_from_text_estimate(*, prompt_text: str, completion_text: str) -> GenerationUsage:
    prompt = estimate_token_count(prompt_text)
    completion = estimate_token_count(completion_text)
    return GenerationUsage(
        prompt_tokens=prompt,
        completion_tokens=completion,
        total_tokens=prompt + completion,
        estimated=True,
    )
