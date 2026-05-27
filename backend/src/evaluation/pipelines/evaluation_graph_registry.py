from __future__ import annotations

from typing import Any

_compiled: Any = None


def get_compiled_evaluation_graph() -> Any:
    global _compiled
    if _compiled is None:
        from src.evaluation.pipelines.evaluation_graph import build_evaluation_graph

        _compiled = build_evaluation_graph().compile()
    return _compiled


def register_evaluation_graph() -> Any:
    return get_compiled_evaluation_graph()
