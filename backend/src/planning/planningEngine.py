"""PlanningEngine coordinating rules evaluation and generating ExecutionPlan."""

from time import perf_counter

from src.core.appEnvironment import AppEnvironment
from src.observability.structuredLogger import get_logger
from src.planning.executionPlan import ExecutionPlan
from src.planning.planningRules import PlanningRules
from src.runtimeContext.runtimeContext import RuntimeContext

logger = get_logger("planning.engine")


class PlanningEngine:
    """Coordinator executing planning rules and producing immutable ExecutionPlans."""

    def __init__(self, settings: AppEnvironment) -> None:
        self._settings = settings

    def plan(self, context: RuntimeContext) -> ExecutionPlan:
        """Assembles ExecutionPlan by evaluating planning rules against context."""
        start_time = perf_counter()
        logger.info(
            "planning_started",
            user_id=str(context.session.user_id),
            organization_id=str(context.session.organization_id),
        )

        workflow = PlanningRules.determine_workflow(context)
        retrieval = PlanningRules.determine_retrieval(context)
        budget = PlanningRules.determine_budget(context, self._settings)
        strategy = PlanningRules.determine_strategy(workflow)

        plan = ExecutionPlan(
            workflow=workflow,
            retrieval=retrieval,
            budget=budget,
            strategy=strategy,
        )

        duration = perf_counter() - start_time
        logger.info(
            "planning_completed",
            user_id=str(context.session.user_id),
            organization_id=str(context.session.organization_id),
            selected_workflow=plan.workflow.selected_workflow,
            retrieval_decision=plan.retrieval.need_retrieval,
            execution_strategy=plan.strategy.concurrency,
            planning_duration_seconds=round(duration, 4),
        )
        return plan
