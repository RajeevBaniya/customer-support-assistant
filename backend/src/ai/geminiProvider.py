import json
from collections.abc import AsyncIterator
from typing import Any, cast
from urllib.parse import quote

import httpx

from src.ai.generationUsage import GenerationUsage, usage_from_provider_counts
from src.core.appEnvironment import AppEnvironment


def _parse_gemini_usage(data: dict[str, Any]) -> GenerationUsage | None:
    meta = cast(dict[str, Any], data.get("usageMetadata") or {})
    if not meta:
        return None
    prompt = meta.get("promptTokenCount")
    completion = meta.get("candidatesTokenCount")
    if prompt is None and completion is None:
        return None
    return usage_from_provider_counts(
        prompt_tokens=int(prompt or 0),
        completion_tokens=int(completion or 0),
    )


async def gemini_chat(
    settings: AppEnvironment,
    *,
    system: str,
    user: str,
    timeout_seconds: float,
) -> tuple[str, GenerationUsage | None]:
    key = settings.gemini_api_key
    if not key or not str(key).strip():
        raise RuntimeError("gemini_key_missing")
    model = quote(settings.gemini_model.strip(), safe=".-_")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={str(key).strip()}"
    )
    body: dict[str, Any] = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048},
    }
    timeout = httpx.Timeout(timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=body)
        response.raise_for_status()
        data = response.json()
    candidates = cast(list[dict[str, Any]], data.get("candidates") or [])
    if not candidates:
        raise RuntimeError("gemini_empty_candidates")
    content = cast(dict[str, Any], candidates[0].get("content") or {})
    parts = cast(list[dict[str, Any]], content.get("parts") or [])
    if not parts:
        raise RuntimeError("gemini_empty_parts")
    text = parts[0].get("text")
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError("gemini_empty_text")
    return text.strip(), _parse_gemini_usage(data)


def _gemini_stream_text_from_obj(obj: dict[str, Any]) -> str | None:
    candidates = cast(list[dict[str, Any]], obj.get("candidates") or [])
    if not candidates:
        return None
    content = cast(dict[str, Any], candidates[0].get("content") or {})
    parts = cast(list[dict[str, Any]], content.get("parts") or [])
    if not parts:
        return None
    text = parts[0].get("text")
    if isinstance(text, str) and text:
        return text
    return None


async def gemini_chat_stream(
    settings: AppEnvironment,
    *,
    system: str,
    user: str,
    timeout_seconds: float,
) -> AsyncIterator[str]:
    key = settings.gemini_api_key
    if not key or not str(key).strip():
        raise RuntimeError("gemini_key_missing")
    model = quote(settings.gemini_model.strip(), safe=".-_")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:streamGenerateContent?key={str(key).strip()}&alt=sse"
    )
    body: dict[str, Any] = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048},
    }
    timeout = httpx.Timeout(timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("POST", url, json=body) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                if not line.startswith("data: "):
                    continue
                raw = line.removeprefix("data: ").strip()
                try:
                    obj = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                piece = _gemini_stream_text_from_obj(obj)
                if piece:
                    yield piece
