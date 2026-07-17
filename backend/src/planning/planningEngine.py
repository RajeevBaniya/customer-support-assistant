"""PlanningEngine coordinating rules evaluation and generating ExecutionPlan."""

from time import perf_counter

from src.core.appEnvironment import AppEnvironment
from src.observability.structuredLogger import get_logger
from src.planning.executionPlan import ExecutionPlan
from src.planning.plannerAgentService import PlannerAgentService
from src.runtimeContext.runtimeContext import RuntimeContext

logger = get_logger("planning.engine")


class PlanningEngine:
    """Coordinator executing planning rules and producing immutable ExecutionPlans."""

    def __init__(self, settings: AppEnvironment) -> None:
        self._settings = settings

    async def plan(self, context: RuntimeContext) -> ExecutionPlan:
        """Assembles ExecutionPlan by evaluating planning rules against context."""
        start_time = perf_counter()
        logger.info(
            "planning_started",
            user_id=str(context.session.user_id),
            organization_id=str(context.session.organization_id),
        )

        agent = PlannerAgentService(self._settings)
        plan = await agent.generate_plan(context)

        duration = perf_counter() - start_time
        logger.info(
            "planning_completed",
            user_id=str(context.session.user_id),
            organization_id=str(context.session.organization_id),
            selected_workflow=plan.workflow.selected_workflow,
            retrieval_decision=plan.retrieval.need_retrieval,
            execution_strategy=plan.strategy.concurrency,
            planning_duration_seconds=round(duration, 4),
            user_intent=plan.user_intent,
            execution_type=plan.execution_type,
            complexity=plan.complexity,
            confidence=plan.confidence,
            fallback_used=plan.planner_metadata.get("fallback_used", False),
            model_used=plan.planner_metadata.get("model_used"),
            provider_used=plan.planner_metadata.get("provider_used"),
        )
        return plan
