from src.documents.ingestionRetryPolicy import (
    IngestionTransientError,
    backoff_seconds,
    is_transient_ingestion_failure,
)


def test_transient_error_classified() -> None:
    assert is_transient_ingestion_failure(IngestionTransientError("x")) is True


def test_timeout_error_classified() -> None:
    assert is_transient_ingestion_failure(TimeoutError()) is True


def test_value_error_not_transient() -> None:
    assert is_transient_ingestion_failure(ValueError("bad")) is False


def test_backoff_grows_then_caps() -> None:
    assert backoff_seconds(attempt=1, base=10) == 10
    assert backoff_seconds(attempt=3, base=10) == 40
    assert backoff_seconds(attempt=20, base=10) == 600
