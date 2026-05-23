import logging
import sys
from typing import Any, cast

import structlog


def configure_structured_logging(*, debug: bool) -> None:
    log_level = logging.DEBUG if debug else logging.INFO

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.typing.FilteringBoundLogger:
    return cast(structlog.typing.FilteringBoundLogger, structlog.get_logger(name))


def bind_request_context(**context: Any) -> None:
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(**context)


def clear_request_context() -> None:
    structlog.contextvars.clear_contextvars()
