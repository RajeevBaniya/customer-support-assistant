from __future__ import annotations

from time import perf_counter
from typing import TYPE_CHECKING

from src.core.appEnvironment import AppEnvironment
from src.observability.structuredLogger import get_logger
from src.response.responseMetrics import ResponseMetrics
from src.response.responseModels import ResponseRequest
from src.response.responseResult import ResponseResult

if TYPE_CHECKING:
    from src.observability.observabilityEngine import ObservabilityEngine

logger = get_logger("response.engine")


class ResponseEngine:
    """Compilation boundary layer formatting GenerationResult and citations into ResponseResult."""

    def __init__(
        self, settings: AppEnvironment, observability: ObservabilityEngine | None = None
    ) -> None:
        self._settings = settings
        self._observability = observability

    def compile(self, request: ResponseRequest) -> ResponseResult:
        """Assembles assistant response from generation outputs and citations."""
        start_time = perf_counter()

        gen = request.generation_result
        pkg = request.context_package

        assistant_text = gen.assistant_text
        citations = pkg.citations.citations
        provider_used = gen.provider_used
        model_used = gen.model_used
        finish_reason = gen.finish_reason
        fallback_used = gen.fallback_used
        usage = gen.token_usage

        execution_metadata = {
            "provider_used": provider_used,
            "model_used": model_used,
            "finish_reason": finish_reason,
            "fallback_used": fallback_used,
            "latency_ms": gen.latency_ms,
            "usage": usage,
        }

        duration_ms = (perf_counter() - start_time) * 1000.0

        metrics = ResponseMetrics(
            response_latency_ms=duration_ms,
            response_size_chars=len(assistant_text),
            citation_count=len(citations),
            provider=provider_used,
            fallback=fallback_used,
        )

        if self._observability:
            self._observability.start_stage("response")
            self._observability.record_response(
                provider=provider_used,
                model=model_used,
                fallback_used=fallback_used,
                citation_count=len(citations),
                response_size_chars=len(assistant_text),
            )
            self._observability.end_stage("response", status="success")

        return ResponseResult(
            assistant_text=assistant_text,
            citations=citations,
            provider_used=provider_used,
            model_used=model_used,
            finish_reason=finish_reason,
            fallback_used=fallback_used,
            usage=usage,
            execution_metadata=execution_metadata,
            response_metrics=metrics,
        )
