from __future__ import annotations

from typing import TypedDict


class EvaluationHealthBundle(TypedDict, total=False):
    evaluation_engine_ready: bool
    benchmark_registry_ready: bool
    evaluation_engine_error: str
    benchmark_registry_error: str


def evaluation_health_bundle() -> EvaluationHealthBundle:
    out: EvaluationHealthBundle = {
        "evaluation_engine_ready": False,
        "benchmark_registry_ready": False,
    }
    try:
        from src.evaluationEngine.evaluationEngine import EvaluationEngine  # noqa: F401

        out["evaluation_engine_ready"] = True
    except Exception as exc:
        out["evaluation_engine_error"] = str(exc)

    try:
        from src.jobs import evaluationTasks as evaluation_tasks

        name = getattr(evaluation_tasks.run_benchmark_evaluation_task, "name", "")
        if not str(name).strip():
            raise RuntimeError("benchmark_task_unnamed")
        out["benchmark_registry_ready"] = True
    except Exception as exc:
        out["benchmark_registry_error"] = str(exc)

    return out
