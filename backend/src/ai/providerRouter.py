from collections.abc import AsyncIterator

from src.ai.geminiProvider import gemini_chat, gemini_chat_stream
from src.ai.groqProvider import groq_chat, groq_chat_stream
from src.core.appEnvironment import AppEnvironment
from src.shared.customExceptions import BaseApplicationException


def _other_provider(name: str) -> str:
    if name == "groq":
        return "gemini"
    return "groq"


async def complete_with_fallback(
    settings: AppEnvironment,
    *,
    system: str,
    user: str,
) -> tuple[str, str]:
    timeout = float(settings.llm_timeout_seconds)
    primary = settings.active_llm_provider.strip().lower()
    order = [primary, _other_provider(primary)]
    last_reason = "no_provider_attempted"
    for name in order:
        try:
            if name == "groq":
                text = await groq_chat(settings, system=system, user=user, timeout_seconds=timeout)
                return text, "groq"
            if name == "gemini":
                text = await gemini_chat(
                    settings,
                    system=system,
                    user=user,
                    timeout_seconds=timeout,
                )
                return text, "gemini"
        except Exception as exc:
            last_reason = str(exc)
            continue
    raise BaseApplicationException(
        "No LLM provider could complete the request",
        error_code="rag_provider_unavailable",
        status_code=503,
        details={"reason": last_reason},
    )


async def stream_chat_with_fallback(
    settings: AppEnvironment,
    *,
    system: str,
    user: str,
) -> AsyncIterator[tuple[str, str]]:
    timeout = float(settings.llm_timeout_seconds)
    primary = settings.active_llm_provider.strip().lower()
    order = [primary, _other_provider(primary)]
    last_reason = "no_provider_attempted"
    emitted = False
    for name in order:
        try:
            if name == "groq":
                gen = groq_chat_stream(settings, system=system, user=user, timeout_seconds=timeout)
            elif name == "gemini":
                gen = gemini_chat_stream(
                    settings,
                    system=system,
                    user=user,
                    timeout_seconds=timeout,
                )
            else:
                continue
            async for delta in gen:
                emitted = True
                yield name, delta
            return
        except Exception as exc:
            last_reason = str(exc)
            if emitted:
                raise
            continue
    raise BaseApplicationException(
        "No LLM provider could stream the request",
        error_code="rag_provider_unavailable",
        status_code=503,
        details={"reason": last_reason},
    )
