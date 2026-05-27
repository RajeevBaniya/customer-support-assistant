from sqlalchemy.ext.asyncio import AsyncEngine

from src.observability.structuredLogger import get_logger

logger = get_logger(__name__)


def pool_snapshot(engine: AsyncEngine) -> dict[str, int]:
    pool = engine.pool
    try:
        checked_in = getattr(pool, "checked_in", None) or getattr(pool, "checkedin", None)
        checked_out = getattr(pool, "checked_out", None) or getattr(pool, "checkedout", None)
        size_fn = getattr(pool, "size", None)
        overflow_fn = getattr(pool, "overflow", None)
        return {
            "pool_size": int(size_fn()) if callable(size_fn) else 0,
            "checked_in": int(checked_in()) if callable(checked_in) else 0,
            "checked_out": int(checked_out()) if callable(checked_out) else 0,
            "overflow": int(overflow_fn()) if callable(overflow_fn) else 0,
        }
    except Exception as exc:
        logger.warning(
            "pool_snapshot_failed",
            component="database.pool_metrics.pool_snapshot",
            exc_type=type(exc).__name__,
            exc_message=str(exc),
            exc_info=True,
        )
        return {
            "pool_size": 0,
            "checked_in": 0,
            "checked_out": 0,
            "overflow": 0,
        }
