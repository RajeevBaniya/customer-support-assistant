from src.observability.observability_health import observability_health_bundle


def test_observability_health_bundle_ready() -> None:
    bundle = observability_health_bundle()
    assert bundle.get("metrics_ready") is True
    assert bundle.get("tracing_ready") is True
    assert bundle.get("observability_ready") is True
