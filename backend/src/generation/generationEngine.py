from __future__ import annotations

from collections.abc import AsyncIterator
from time import perf_counter
from typing import TYPE_CHECKING

from src.ai.providerRouter import complete_with_fallback, stream_chat_with_fallback
from src.core.appEnvironment import AppEnvironment
from src.generation.generationModels import GenerationRequest
from src.generation.generationResult import GenerationResult
from src.observability.structuredLogger import get_logger
from src.shared.customExceptions import BaseApplicationException

if TYPE_CHECKING:
    from src.observability.observabilityEngine import ObservabilityEngine

logger = get_logger("generation.engine")


class GenerationEngine:
    """Execution boundary layer coordinating LLM provider calls and exception mapping."""

    def __init__(
        self, settings: AppEnvironment, observability: ObservabilityEngine | None = None
    ) -> None:
        self._settings = settings
        self._observability = observability

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Executes LLM chat completion synchronously with fallback handling."""
        start_time = perf_counter()
        system = request.context_package.instructions.system_prompt
        user = request.context_package.instructions.user_prompt

        settings = self._settings
        if request.provider_override is not None:
            settings = self._settings.model_copy(
                update={"active_llm_provider": request.provider_override}
            )

        try:
            answer, provider = await complete_with_fallback(
                settings,
                system=system,
                user=user,
                organization_id=request.organization_id,
                route_type="rag",
                is_evaluation=request.is_evaluation,
            )
        except BaseApplicationException:
            raise
        except Exception as exc:
            raise BaseApplicationException(
                f"LLM Generation failed: {str(exc)}",
                error_code="generation_failed",
                status_code=502,
                details={"reason": str(exc)},
            ) from exc

        duration_ms = (perf_counter() - start_time) * 1000.0
        model = settings.groq_model if provider == "groq" else settings.gemini_model
        fallback_used = provider != settings.active_llm_provider.strip().lower()

        if self._observability:
            self._observability.start_stage("generation")
            self._observability.record_generation(
                provider=provider,
                model=model,
                duration_ms=duration_ms,
                fallback_used=fallback_used,
                finish_reason="stop",
                organization_id=request.organization_id,
                token_usage=None,
            )
            self._observability.end_stage(
                "generation",
                status="success",
                metadata={"provider": provider, "fallback_used": fallback_used},
            )

        return GenerationResult(
            assistant_text=answer,
            finish_reason="stop",
            provider_used=provider,
            model_used=model,
            token_usage=None,
            latency_ms=duration_ms,
            fallback_used=fallback_used,
        )

    async def stream_generate(
        self, request: GenerationRequest
    ) -> AsyncIterator[GenerationResult]:
        """Streams LLM chat completion chunk-by-chunk with fallback handling."""
        start_time = perf_counter()
        system = request.context_package.instructions.system_prompt
        user = request.context_package.instructions.user_prompt

        settings = self._settings
        if request.provider_override is not None:
            settings = self._settings.model_copy(
                update={"active_llm_provider": request.provider_override}
            )

        try:
            gen = stream_chat_with_fallback(
                settings,
                system=system,
                user=user,
                organization_id=request.organization_id,
                route_type="chat_stream",
                is_evaluation=request.is_evaluation,
            )

            active_provider = settings.active_llm_provider.strip().lower()
            last_provider = "none"
            last_model = "none"
            last_duration = 0.0
            last_fallback = False

            async for provider, delta in gen:
                duration_ms = (perf_counter() - start_time) * 1000.0
                model = settings.groq_model if provider == "groq" else settings.gemini_model
                fallback_used = provider != active_provider

                last_provider = provider
                last_model = model
                last_duration = duration_ms
                last_fallback = fallback_used

                yield GenerationResult(
                    assistant_text=delta,
                    finish_reason=None,
                    provider_used=provider,
                    model_used=model,
                    token_usage=None,
                    latency_ms=duration_ms,
                    fallback_used=fallback_used,
                )

            if self._observability:
                self._observability.start_stage("generation")
                self._observability.record_generation(
                    provider=last_provider,
                    model=last_model,
                    duration_ms=last_duration,
                    fallback_used=last_fallback,
                    finish_reason="stop",
                    organization_id=request.organization_id,
                    token_usage=None,
                )
                self._observability.end_stage(
                    "generation",
                    status="success",
                    metadata={"provider": last_provider, "fallback_used": last_fallback},
                )
        except BaseApplicationException:
            raise
        except Exception as exc:
            raise BaseApplicationException(
                f"LLM Stream Generation failed: {str(exc)}",
                error_code="generation_failed",
                status_code=502,
                details={"reason": str(exc)},
            ) from exc
