from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID

from src.ai.geminiProvider import gemini_chat, gemini_chat_stream
from src.ai.generationUsage import GenerationUsage, usage_from_text_estimate
from src.ai.groqProvider import groq_chat, groq_chat_stream
from src.core.appEnvironment import AppEnvironment
from src.observability.metrics.recorders import record_generation_usage
from src.shared.customExceptions import BaseApplicationException


def _other_provider(name: str) -> str:
    if name == "groq":
        return "gemini"
    return "groq"


def _record_usage(
    *,
    organization_id: UUID | None,
    provider: str,
    route_type: str,
    usage: GenerationUsage | None,
    prompt_text: str,
    completion_text: str,
) -> None:
    if usage is None:
        usage = usage_from_text_estimate(prompt_text=prompt_text, completion_text=completion_text)
    record_generation_usage(
        organization_id=organization_id,
        provider=provider,
        route_type=route_type,
        usage=usage,
    )


async def complete_with_fallback(
    settings: AppEnvironment,
    *,
    system: str,
    user: str,
    organization_id: UUID | None = None,
    route_type: str = "rag",
) -> tuple[str, str]:
    timeout = float(settings.llm_timeout_seconds)
    primary = settings.active_llm_provider.strip().lower()
    order = [primary, _other_provider(primary)]
    last_reason = "no_provider_attempted"
    prompt_text = f"{system}\n{user}"
    for name in order:
        try:
            if name == "groq":
                text, usage = await groq_chat(
                    settings,
                    system=system,
                    user=user,
                    timeout_seconds=timeout,
                )
                _record_usage(
                    organization_id=organization_id,
                    provider="groq",
                    route_type=route_type,
                    usage=usage,
                    prompt_text=prompt_text,
                    completion_text=text,
                )
                return text, "groq"
            if name == "gemini":
                text, usage = await gemini_chat(
                    settings,
                    system=system,
                    user=user,
                    timeout_seconds=timeout,
                )
                _record_usage(
                    organization_id=organization_id,
                    provider="gemini",
                    route_type=route_type,
                    usage=usage,
                    prompt_text=prompt_text,
                    completion_text=text,
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
    organization_id: UUID | None = None,
    route_type: str = "chat_stream",
) -> AsyncIterator[tuple[str, str]]:
    timeout = float(settings.llm_timeout_seconds)
    primary = settings.active_llm_provider.strip().lower()
    order = [primary, _other_provider(primary)]
    last_reason = "no_provider_attempted"
    emitted = False
    prompt_text = f"{system}\n{user}"
    parts: list[str] = []
    provider_used = "none"
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
            provider_used = name
            async for delta in gen:
                emitted = True
                parts.append(delta)
                yield name, delta
            completion = "".join(parts)
            _record_usage(
                organization_id=organization_id,
                provider=provider_used,
                route_type=route_type,
                usage=usage_from_text_estimate(prompt_text=prompt_text, completion_text=completion),
                prompt_text=prompt_text,
                completion_text=completion,
            )
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
