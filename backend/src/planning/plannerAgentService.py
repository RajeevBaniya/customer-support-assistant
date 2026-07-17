import json
from pathlib import Path
from time import perf_counter
from typing import Any

from pydantic import BaseModel, Field

from src.ai.providerRegistry import ProviderRegistry
from src.core.appEnvironment import AppEnvironment
from src.observability.structuredLogger import get_logger
from src.planning.executionPlan import ExecutionPlan
from src.planning.planningRules import PlanningRules
from src.runtimeContext.runtimeContext import RuntimeContext

logger = get_logger("planning.agent")

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "ai" / "prompts"


def _read_prompt(name: str) -> str:
    return (_PROMPTS_DIR / name).read_text(encoding="utf-8").strip()


class PlannerAgentOutput(BaseModel):
    """Pydantic schema for validating LLM structured planning output."""

    user_intent: str = Field(min_length=1)
    execution_type: str = Field(min_length=1)
    complexity: str = Field(min_length=1)
    retrieval_required: bool
    retrieval_strategy: str = Field(min_length=1)
    history_required: bool
    context_required: bool
    multiple_retrieval_passes: bool
    reviewer_enabled: bool
    tool_usage_beneficial: bool
    estimated_steps: int = Field(ge=1)
    confidence: float = Field(ge=0.0, le=1.0)


class PlannerAgentService:
    """Intelligent agent analyzing user requests to generate ExecutionPlans."""

    def __init__(self, settings: AppEnvironment) -> None:
        self._settings = settings

    async def generate_plan(self, context: RuntimeContext) -> ExecutionPlan:
        """Assembles the ExecutionPlan using LLM planning or deterministic fallback."""
        start_time = perf_counter()

        query = context.execution.query
        selected_docs_count = len(context.execution.document_ids or [])
        has_history = (
            context.conversation is not None
            and len(context.conversation.recent_messages) > 1
        )

        model = self._settings.planning_model
        api_key = self._settings.planning_api_key

        if not api_key or not str(api_key).strip():
            logger.warning(
                "planner_agent_credentials_missing",
                reason="Planning API key not configured",
            )
            return self._build_deterministic_fallback(
                context, {"fallback_reason": "credentials_missing"}
            )

        try:
            system_prompt = _read_prompt("planner_system.txt")
            user_prompt = _read_prompt("planner_user.txt").format(
                query=query,
                selected_docs_count=selected_docs_count,
                has_history=has_history,
            )

            provider_name, executor = ProviderRegistry.get_provider(model)
            timeout = float(self._settings.llm_timeout_seconds)

            text_response, usage = await executor.chat(
                self._settings,
                model=model,
                api_key=api_key,
                system=system_prompt,
                user=user_prompt,
                timeout_seconds=timeout,
            )

            raw_data = self._clean_and_parse_json(text_response)
            parsed_output = PlannerAgentOutput.model_validate(raw_data)

            workflow = PlanningRules.determine_workflow(context)
            retrieval = PlanningRules.determine_retrieval(context)

            if retrieval.need_retrieval != parsed_output.retrieval_required:
                from src.planning.planningModels import MetadataFilter, RetrievalDecision

                if parsed_output.retrieval_required:
                    meta = MetadataFilter(
                        organization_id=context.session.organization_id,
                        document_ids=context.execution.document_ids or [],
                    )
                    mode = parsed_output.retrieval_strategy
                    if mode == "none":
                        mode = "semantic"
                    retrieval = RetrievalDecision(
                        need_retrieval=True,
                        retrieval_mode=mode,
                        metadata_filter=meta,
                    )
                else:
                    retrieval = RetrievalDecision(
                        need_retrieval=False,
                        retrieval_mode="none",
                        metadata_filter=None,
                    )

            budget = PlanningRules.determine_budget(context, self._settings)
            strategy = PlanningRules.determine_strategy(workflow)

            duration_ms = (perf_counter() - start_time) * 1000.0
            metadata = {
                "latency_ms": duration_ms,
                "confidence": parsed_output.confidence,
                "execution_type": parsed_output.execution_type,
                "retrieval_strategy": parsed_output.retrieval_strategy,
                "version": "1.0.0",
                "provider_used": provider_name,
                "model_used": model,
                "fallback_used": False,
            }

            return ExecutionPlan(
                user_intent=parsed_output.user_intent,
                execution_type=parsed_output.execution_type,
                complexity=parsed_output.complexity,
                retrieval_required=parsed_output.retrieval_required,
                retrieval_strategy=parsed_output.retrieval_strategy,
                history_required=parsed_output.history_required,
                context_required=parsed_output.context_required,
                multiple_retrieval_passes=parsed_output.multiple_retrieval_passes,
                reviewer_enabled=parsed_output.reviewer_enabled,
                tool_usage_beneficial=parsed_output.tool_usage_beneficial,
                estimated_steps=parsed_output.estimated_steps,
                confidence=parsed_output.confidence,
                planner_metadata=metadata,
                workflow=workflow,
                retrieval=retrieval,
                budget=budget,
                strategy=strategy,
            )

        except Exception as exc:
            logger.exception("planner_agent_failed", reason=str(exc))
            return self._build_deterministic_fallback(context, {"fallback_reason": str(exc)})

    def _build_deterministic_fallback(
        self, context: RuntimeContext, metadata: dict[str, Any]
    ) -> ExecutionPlan:
        """Constructs a valid, safe ExecutionPlan using deterministic rules."""
        workflow = PlanningRules.determine_workflow(context)
        retrieval = PlanningRules.determine_retrieval(context)
        budget = PlanningRules.determine_budget(context, self._settings)
        strategy = PlanningRules.determine_strategy(workflow)

        metadata.update(
            {
                "fallback_used": True,
                "version": "1.0.0",
            }
        )

        has_history = (
            context.conversation is not None
            and len(context.conversation.recent_messages) > 1
        )

        return ExecutionPlan(
            user_intent="question",
            execution_type="rag" if retrieval.need_retrieval else "direct_answer",
            complexity="low",
            retrieval_required=retrieval.need_retrieval,
            retrieval_strategy=retrieval.retrieval_mode,
            history_required=has_history,
            context_required=True,
            multiple_retrieval_passes=False,
            reviewer_enabled=False,
            tool_usage_beneficial=False,
            estimated_steps=2 if retrieval.need_retrieval else 1,
            confidence=1.0,
            planner_metadata=metadata,
            workflow=workflow,
            retrieval=retrieval,
            budget=budget,
            strategy=strategy,
        )

    def _clean_and_parse_json(self, text: str) -> dict[str, Any]:
        """Cleans and extracts JSON payload from markdown fences or raw output."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
        parsed = json.loads(cleaned)
        if not isinstance(parsed, dict):
            raise ValueError("LLM response did not parse as a JSON object")
        return parsed
