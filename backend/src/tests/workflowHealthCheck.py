from src.observability.workflow_health import workflow_health_bundle


def test_workflow_health_bundle_engine_ready() -> None:
    bundle = workflow_health_bundle()
    assert bundle.get("workflow_engine_ready") is True
    assert bundle.get("graph_registry_ready") is True
