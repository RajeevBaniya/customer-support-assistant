import pytest

from src.observability.analytics.analytics_time_window import clamp_analytics_hours


def test_clamp_analytics_hours_default() -> None:
    assert clamp_analytics_hours(0) == 24


def test_clamp_analytics_hours_rejects_over_limit() -> None:
    with pytest.raises(ValueError, match="analytics_hours_over_limit"):
        clamp_analytics_hours(200)
