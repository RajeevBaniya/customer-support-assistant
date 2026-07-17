from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from src.ai.generationUsage import GenerationUsage
from src.core.appEnvironment import AppEnvironment


class LLMProviderExecutor(Protocol):
    """Protocol for provider execution details."""

    async def chat(
        self,
        settings: AppEnvironment,
        *,
        model: str,
        api_key: str,
        system: str,
        user: str,
        timeout_seconds: float,
    ) -> tuple[str, GenerationUsage | None]:
        ...

    async def chat_stream(
        self,
        settings: AppEnvironment,
        *,
        model: str,
        api_key: str,
        system: str,
        user: str,
        timeout_seconds: float,
    ) -> AsyncIterator[str]:
        ...


class GroqProviderExecutor:
    """Executor coordinating calls with the Groq API provider."""

    async def chat(
        self,
        settings: AppEnvironment,
        *,
        model: str,
        api_key: str,
        system: str,
        user: str,
        timeout_seconds: float,
    ) -> tuple[str, GenerationUsage | None]:
        from src.ai.groqProvider import groq_chat

        return await groq_chat(
            settings,
            model=model,
            api_key=api_key,
            system=system,
            user=user,
            timeout_seconds=timeout_seconds,
        )

    async def chat_stream(
        self,
        settings: AppEnvironment,
        *,
        model: str,
        api_key: str,
        system: str,
        user: str,
        timeout_seconds: float,
    ) -> AsyncIterator[str]:
        from src.ai.groqProvider import groq_chat_stream

        return groq_chat_stream(
            settings,
            model=model,
            api_key=api_key,
            system=system,
            user=user,
            timeout_seconds=timeout_seconds,
        )


class GeminiProviderExecutor:
    """Executor coordinating calls with the Gemini API provider."""

    async def chat(
        self,
        settings: AppEnvironment,
        *,
        model: str,
        api_key: str,
        system: str,
        user: str,
        timeout_seconds: float,
    ) -> tuple[str, GenerationUsage | None]:
        from src.ai.geminiProvider import gemini_chat

        return await gemini_chat(
            settings,
            model=model,
            api_key=api_key,
            system=system,
            user=user,
            timeout_seconds=timeout_seconds,
        )

    async def chat_stream(
        self,
        settings: AppEnvironment,
        *,
        model: str,
        api_key: str,
        system: str,
        user: str,
        timeout_seconds: float,
    ) -> AsyncIterator[str]:
        from src.ai.geminiProvider import gemini_chat_stream

        return gemini_chat_stream(
            settings,
            model=model,
            api_key=api_key,
            system=system,
            user=user,
            timeout_seconds=timeout_seconds,
        )


class ProviderRegistry:
    """Factory and registry matching LLM model names to their provider executors."""

    _models: dict[str, str] = {
        "llama-3.1-8b-instant": "groq",
        "gemini-1.5-flash": "gemini",
    }

    _providers: dict[str, LLMProviderExecutor] = {
        "groq": GroqProviderExecutor(),
        "gemini": GeminiProviderExecutor(),
    }

    @classmethod
    def get_provider(cls, model_name: str) -> tuple[str, LLMProviderExecutor]:
        """Resolves the provider name and executor instance for a given model."""
        name = model_name.strip().lower()
        provider_name = cls._models.get(name)
        if not provider_name:
            if "gemini" in name:
                provider_name = "gemini"
            else:
                provider_name = "groq"

        executor = cls._providers.get(provider_name)
        if not executor:
            raise ValueError(f"No executor registered for provider: {provider_name}")

        return provider_name, executor
