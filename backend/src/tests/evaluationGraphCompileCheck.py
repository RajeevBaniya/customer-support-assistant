from src.evaluation.pipelines.evaluation_graph_registry import register_evaluation_graph


def test_evaluation_graph_compiles() -> None:
    app = register_evaluation_graph()
    assert app is not None
