import os
from unittest.mock import patch

import pytest

from src.ai.providerRouter import stream_chat_with_fallback
from src.core.appEnvironment import AppEnvironment
from src.shared.customExceptions import BaseApplicationException


def _settings() -> AppEnvironment:
    return AppEnvironment(
        APP_ENV="test",
        DEBUG=False,
        DATABASE_URL=(
            os.environ.get("DATABASE_URL")
            or "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/recallstack"
        ),
        ACTIVE_LLM_PROVIDER="groq",
    )


class _FailStream:
    def __aiter__(self) -> "_FailStream":
        return self

    async def __anext__(self) -> str:
        raise RuntimeError("stream_down")


class _GeminiOneToken:
    def __aiter__(self) -> "_GeminiOneToken":
        self._sent = False
        return self

    async def __anext__(self) -> str:
        if self._sent:
            raise StopAsyncIteration
        self._sent = True
        return "x"


class _GroqThenFail:
    def __aiter__(self) -> "_GroqThenFail":
        self._step = 0
        return self

    async def __anext__(self) -> str:
        self._step += 1
        if self._step == 1:
            return "a"
        raise RuntimeError("mid_fail")


class _NeverUsed:
    def __aiter__(self) -> "_NeverUsed":
        return self

    async def __anext__(self) -> str:
        raise AssertionError("gemini should not run")


@pytest.mark.asyncio
async def test_stream_fallback_before_first_token() -> None:
    with (
        patch("src.ai.providerRouter.groq_chat_stream", lambda *_a, **_k: _FailStream()),
        patch("src.ai.providerRouter.gemini_chat_stream", lambda *_a, **_k: _GeminiOneToken()),
    ):
        rows: list[tuple[str, str]] = []
        async for row in stream_chat_with_fallback(_settings(), system="s", user="u"):
            rows.append(row)
    assert rows == [("gemini", "x")]


@pytest.mark.asyncio
async def test_stream_no_fallback_after_first_token() -> None:
    with (
        patch("src.ai.providerRouter.groq_chat_stream", lambda *_a, **_k: _GroqThenFail()),
        patch("src.ai.providerRouter.gemini_chat_stream", lambda *_a, **_k: _NeverUsed()),
    ):
        with pytest.raises(RuntimeError, match="mid_fail"):
            async for _ in stream_chat_with_fallback(_settings(), system="s", user="u"):
                pass


@pytest.mark.asyncio
async def test_stream_both_fail_before_tokens_raises_app_exception() -> None:
    with (
        patch("src.ai.providerRouter.groq_chat_stream", lambda *_a, **_k: _FailStream()),
        patch("src.ai.providerRouter.gemini_chat_stream", lambda *_a, **_k: _FailStream()),
    ):
        with pytest.raises(BaseApplicationException) as excinfo:
            async for _ in stream_chat_with_fallback(_settings(), system="s", user="u"):
                pass
        assert excinfo.value.error_code == "rag_provider_unavailable"
