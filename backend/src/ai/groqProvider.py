import json
from collections.abc import AsyncIterator
from typing import Any, cast

import httpx

from src.core.appEnvironment import AppEnvironment


async def groq_chat(
    settings: AppEnvironment,
    *,
    system: str,
    user: str,
    timeout_seconds: float,
) -> str:
    key = settings.groq_api_key
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
    return content.strip()


async def groq_chat_stream(
    settings: AppEnvironment,
    *,
    system: str,
    user: str,
    timeout_seconds: float,
) -> AsyncIterator[str]:
    key = settings.groq_api_key
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
