import logging
import sys

import structlog

from backend.app.config import settings


def setup_logging() -> None:
    """Configures structured logging with structlog.

    In production/default, logs are formatted as JSON.
    Standard logging is also intercepted and routed through structlog.
    """
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Use JSONRenderer for structured production logs
# ConsoleRenderer can be enabled separately for local development
    # We will use JSONRenderer by default for production quality
    structlog.configure(
        processors=shared_processors + [structlog.processors.JSONRenderer()],
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        cache_logger_on_first_use=True,
    )

    # Configure the standard library logging to intercept logs
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Intercept third-party logs (e.g. uvicorn, sqlalchemy)
    for logger_name in (
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "sqlalchemy.engine",
    ):
        logger = logging.getLogger(logger_name)
        logger.handlers = []
        logger.propagate = True


logger = structlog.get_logger()
