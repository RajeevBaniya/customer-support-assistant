import json
from collections.abc import AsyncIterator
from typing import Any, cast

import httpx

from src.ai.generationUsage import GenerationUsage, usage_from_provider_counts
from src.core.appEnvironment import AppEnvironment


def _parse_groq_usage(data: dict[str, Any]) -> GenerationUsage | None:
    usage = cast(dict[str, Any], data.get("usage") or {})
    if not usage:
        return None
    prompt = usage.get("prompt_tokens")
    completion = usage.get("completion_tokens")
    if prompt is None and completion is None:
        return None
    return usage_from_provider_counts(
        prompt_tokens=int(prompt or 0),
        completion_tokens=int(completion or 0),
    )


async def groq_chat(
    settings: AppEnvironment,
    *,
    api_key: str,
    system: str,
    user: str,
    timeout_seconds: float,
) -> tuple[str, GenerationUsage | None]:
    key = api_key
    if not key or not str(key).strip():
        raise RuntimeError("groq_key_missing")
    payload: dict[str, Any] = {
        "model": settings.groq_model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    headers = {
        "Authorization": f"Bearer {str(key).strip()}",
        "Content-Type": "application/json",
    }
    timeout = httpx.Timeout(timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
    choices = cast(list[dict[str, Any]], data.get("choices") or [])
    if not choices:
        raise RuntimeError("groq_empty_choices")
    message = cast(dict[str, Any], choices[0].get("message") or {})
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("groq_empty_content")
    return content.strip(), _parse_groq_usage(data)


async def groq_chat_stream(
    settings: AppEnvironment,
    *,
    api_key: str,
    system: str,
    user: str,
    timeout_seconds: float,
) -> AsyncIterator[str]:
    key = api_key
    if not key or not str(key).strip():
        raise RuntimeError("groq_key_missing")
    payload: dict[str, Any] = {
        "model": settings.groq_model,
        "temperature": 0.2,
        "stream": True,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    headers = {
        "Authorization": f"Bearer {str(key).strip()}",
        "Content-Type": "application/json",
    }
    timeout = httpx.Timeout(timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream(
            "POST",
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                if not line.startswith("data: "):
                    continue
                raw = line.removeprefix("data: ").strip()
                if raw == "[DONE]":
                    return
                try:
                    chunk = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                choices = cast(list[dict[str, Any]], chunk.get("choices") or [])
                if not choices:
                    continue
                delta = cast(dict[str, Any], choices[0].get("delta") or {})
                piece = delta.get("content")
                if isinstance(piece, str) and piece:
                    yield piece
