"""ObservabilityEngine encapsulating lifecycle tracking and structured telemetry logging."""

from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.generationUsage import GenerationUsage
from src.core.appEnvironment import AppEnvironment
from src.observability.executionTrace import ExecutionTrace
from src.observability.observabilityModels import StageTelemetry
from src.observability.structuredLogger import get_logger
from src.runtimeTools.metricsTool import (
    MetricsTool,
    RecordGenerationUsageRequest,
    RecordRetrievalRequest,
)

logger = get_logger("observability.engine")


class ObservabilityEngine:
    """Coordinator driving trace capturing, stage metrics aggregation, and logging."""

    def __init__(self, session: AsyncSession, settings: AppEnvironment) -> None:
        self._session = session
        self._settings = settings
        self._metrics_tool = MetricsTool(session, settings)
        self._trace: ExecutionTrace | None = None
        self._stages: dict[str, StageTelemetry] = {}
        self._start_perf: float = 0.0

    def start_trace(
        self,
        workflow_id: str,
        request_id: str | None = None,
        execution_id: UUID | None = None,
    ) -> UUID:
        """Starts a new request trace run."""
        exec_id = execution_id or uuid4()
        self._start_perf = perf_counter()

        self._trace = ExecutionTrace(
            execution_id=exec_id,
            workflow_id=workflow_id,
            request_id=request_id,
            start_time=datetime.now(UTC),
        )
        self._stages = {}
        return exec_id

    def start_stage(self, stage_name: str) -> None:
        """Records beginning timeline markers for a single stage."""
        self._stages[stage_name] = StageTelemetry(
            stage_name=stage_name,
            start_time=datetime.now(UTC),
            status="pending",
        )

    def end_stage(
        self, stage_name: str, status: str = "success", metadata: dict[str, Any] | None = None
    ) -> None:
        """Finalizes timestamps and outcomes of an execution stage."""
        stage = self._stages.get(stage_name)
        if not stage:
            return

        end_time = datetime.now(UTC)
        duration_ms = (end_time - stage.start_time).total_seconds() * 1000.0

        self._stages[stage_name] = StageTelemetry(
            stage_name=stage_name,
            start_time=stage.start_time,
            end_time=end_time,
            duration_ms=duration_ms,
            status=status,
            metadata=metadata or {},
        )

    def record_retrieval(
        self,
        returned_chunks: int,
        top_k: int,
        latency_ms: float,
        retrieval_mode: str,
        organization_id: UUID | None = None,
    ) -> None:
        """Emits standard retrieval completion logs and registers metrics."""
        logger.info(
            "retrieval_completed",
            returned_chunks=returned_chunks,
            top_k=top_k,
            latency_ms=latency_ms,
            retrieval_mode=retrieval_mode,
        )

        req = RecordRetrievalRequest(
            organization_id=organization_id,
            duration_seconds=latency_ms / 1000.0,
            final_chunks=returned_chunks,
            avg_similarity=0.0,
            rerank_input=0,
            post_dedup=returned_chunks,
            near_dup_dropped=0,
            top_k=top_k,
        )
        self._metrics_tool.record_retrieval(req)

    def record_generation(
        self,
        provider: str,
        model: str,
        duration_ms: float,
        fallback_used: bool,
        finish_reason: str,
        organization_id: UUID | None = None,
        token_usage: dict[str, int] | None = None,
    ) -> None:
        """Emits standard generation logs and registers usage metrics."""
        logger.info(
            "generation_completed",
            provider=provider,
            model=model,
            duration_ms=duration_ms,
            fallback_used=fallback_used,
            finish_reason=finish_reason,
        )

        usage = GenerationUsage(
            prompt_tokens=token_usage.get("prompt", 0) if token_usage else 0,
            completion_tokens=token_usage.get("completion", 0) if token_usage else 0,
            total_tokens=token_usage.get("total", 0) if token_usage else 0,
            estimated=False,
        )
        req = RecordGenerationUsageRequest(
            organization_id=organization_id,
            provider=provider,
            route_type="rag",
            usage=usage,
        )
        self._metrics_tool.record_generation(req)

    def record_response(
        self,
        provider: str,
        model: str,
        fallback_used: bool,
        citation_count: int,
        response_size_chars: int,
    ) -> None:
        """Emits standard response compilation logging."""
        logger.info(
            "response_compiled",
            provider=provider,
            model=model,
            fallback_used=fallback_used,
            citation_count=citation_count,
            response_size_chars=response_size_chars,
        )

    def finish_trace(self, status: str = "success") -> ExecutionTrace:
        """Aggregates all execution stats and completes request lifecycle tracing."""
        if not self._trace:
            raise RuntimeError("Trace was not started.")

        end_time = datetime.now(UTC)
        total_ms = (perf_counter() - self._start_perf) * 1000.0

        executed: list[str] = []
        skipped: list[str] = []
        for name, stage in self._stages.items():
            if stage.status == "success":
                executed.append(name)
            else:
                skipped.append(name)

        # Retrieve provider details from generation stage if available
        provider_used = None
        fallback_used = False
        gen_stage = self._stages.get("generation")
        if gen_stage and gen_stage.metadata:
            provider_used = gen_stage.metadata.get("provider")
            fallback_used = bool(gen_stage.metadata.get("fallback_used"))

        completed_trace = ExecutionTrace(
            execution_id=self._trace.execution_id,
            workflow_id=self._trace.workflow_id,
            request_id=self._trace.request_id,
            start_time=self._trace.start_time,
            end_time=end_time,
            total_latency_ms=total_ms,
            executed_stages=executed,
            skipped_stages=skipped,
            provider_used=provider_used,
            fallback_used=fallback_used,
            status=status,
            stages=list(self._stages.values()),
        )

        logger.info(
            "execution_trace_finished",
            execution_id=str(completed_trace.execution_id),
            workflow_id=completed_trace.workflow_id,
            total_latency_ms=completed_trace.total_latency_ms,
            status=completed_trace.status,
            executed_stages=completed_trace.executed_stages,
        )

        self._trace = completed_trace
        return completed_trace
