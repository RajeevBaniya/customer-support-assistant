from src.workflows.trace.workflow_trace_reducer import (
    MAX_TRACE_CHARS,
    MAX_TRACE_ENTRIES,
    workflow_trace_reducer,
)


def test_workflow_trace_reducer_caps_entries() -> None:
    rows = [{"i": n} for n in range(MAX_TRACE_ENTRIES + 10)]
    merged = workflow_trace_reducer([], rows)
    assert len(merged) == MAX_TRACE_ENTRIES
    assert merged[-1]["i"] == MAX_TRACE_ENTRIES + 9


def test_workflow_trace_reducer_caps_chars() -> None:
    fat = [{"k": "x" * 5000}]
    merged = workflow_trace_reducer([], fat)
    total = sum(len(str(e)) for e in merged)
    assert total <= MAX_TRACE_CHARS + 200
