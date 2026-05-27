class IngestionPermanentError(Exception):
    pass


class IngestionTransientError(Exception):
    pass


def is_transient_ingestion_failure(exc: Exception) -> bool:
    if isinstance(exc, IngestionTransientError):
        return True
    if isinstance(exc, TimeoutError | ConnectionError | OSError):
        return True
    name = type(exc).__name__.lower()
    if "timeout" in name:
        return True
    if "connection" in name or "connect" in name:
        return True
    return False


def backoff_seconds(*, attempt: int, base: int) -> int:
    return int(min(600, int(base) * (2 ** max(0, attempt - 1))))
