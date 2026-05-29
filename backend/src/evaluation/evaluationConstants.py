RUN_SINGLE = "single"
RUN_BENCHMARK = "benchmark"

STATUS_PENDING = "pending"
STATUS_QUEUED = "queued"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

HALLUCINATION_PASS_MAX = 0.35
FAITHFULNESS_PASS_MIN = 0.50


def evaluation_result_passes(*, hallucination_score: float, faithfulness_score: float) -> bool:
    return (
        hallucination_score < HALLUCINATION_PASS_MAX and faithfulness_score >= FAITHFULNESS_PASS_MIN
    )
