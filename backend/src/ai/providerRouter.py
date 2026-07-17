from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID

from src.ai.generationUsage import GenerationUsage, usage_from_text_estimate
from src.core.appEnvironment import AppEnvironment
from src.observability.metrics.recorders import record_generation_usage
from src.shared.customExceptions import BaseApplicationException


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
    is_evaluation: bool = False,
) -> tuple[str, str]:
    timeout = float(settings.llm_timeout_seconds)

    if is_evaluation:
        primary_key = settings.evaluation_api_key
        primary_model = settings.evaluation_model
        fallback_key = None
        fallback_model = None
    else:
        primary_key = settings.generation_api_key
        primary_model = settings.generation_model
        fallback_key = settings.fallback_generation_api_key
        fallback_model = settings.fallback_generation_model

    order = []
    if primary_key and str(primary_key).strip() and primary_model:
        order.append((primary_model, primary_key))
    if fallback_key and str(fallback_key).strip() and fallback_model:
        order.append((fallback_model, fallback_key))

    if not order:
        raise BaseApplicationException(
            "No LLM provider keys or models configured",
            error_code="rag_provider_unavailable",
            status_code=503,
            details={"reason": "no_credentials_configured"},
        )

    last_reason = "no_provider_attempted"
    prompt_text = f"{system}\n{user}"

    from src.ai.providerRegistry import ProviderRegistry

    for model, key in order:
        try:
            provider_name, executor = ProviderRegistry.get_provider(model)
            text, usage = await executor.chat(
                settings,
                model=model,
                api_key=key,
                system=system,
                user=user,
                timeout_seconds=timeout,
            )
            _record_usage(
                organization_id=organization_id,
                provider=provider_name,
                route_type=route_type,
                usage=usage,
                prompt_text=prompt_text,
                completion_text=text,
            )
            return text, provider_name
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
    is_evaluation: bool = False,
) -> AsyncIterator[tuple[str, str]]:
    timeout = float(settings.llm_timeout_seconds)

    if is_evaluation:
        primary_key = settings.evaluation_api_key
        primary_model = settings.evaluation_model
        fallback_key = None
        fallback_model = None
    else:
        primary_key = settings.generation_api_key
        primary_model = settings.generation_model
        fallback_key = settings.fallback_generation_api_key
        fallback_model = settings.fallback_generation_model

    order = []
    if primary_key and str(primary_key).strip() and primary_model:
        order.append((primary_model, primary_key))
    if fallback_key and str(fallback_key).strip() and fallback_model:
        order.append((fallback_model, fallback_key))

    if not order:
        raise BaseApplicationException(
            "No LLM provider keys or models configured",
            error_code="rag_provider_unavailable",
            status_code=503,
            details={"reason": "no_credentials_configured"},
        )

    last_reason = "no_provider_attempted"
    emitted = False
    prompt_text = f"{system}\n{user}"
    parts: list[str] = []
    provider_used = "none"

    from src.ai.providerRegistry import ProviderRegistry

    for model, key in order:
        try:
            provider_name, executor = ProviderRegistry.get_provider(model)
            provider_used = provider_name
            gen = await executor.chat_stream(
                settings,
                model=model,
                api_key=key,
                system=system,
                user=user,
                timeout_seconds=timeout,
            )
            async for delta in gen:
                emitted = True
                parts.append(delta)
                yield provider_name, delta
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
