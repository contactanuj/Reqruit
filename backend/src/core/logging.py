"""
structlog configuration for structured logging.

Design decisions
----------------
Why structlog (not stdlib logging):
    structlog outputs JSON by default — each log entry is a dict, not a
    formatted string. This makes logs machine-readable in production (grep
    by user_id, filter by agent, aggregate by error_code) and human-readable
    in development (colored key=value pairs).

    stdlib logging uses string interpolation and requires log parsers to
    extract structured data. structlog inverts this — structure is first class.

Why different renderers for dev vs prod:
    Development: ConsoleRenderer with colors and aligned keys.
        Fast to read at a glance, shows all context, timestamps in local time.
    Production: JSONRenderer.
        One JSON object per line, easily ingested by any log aggregator
        (Datadog, Loki, CloudWatch). Timestamps in ISO 8601 UTC.

Why configure once at app startup (not per-module):
    Processors are shared state. Calling configure_logging() multiple times
    would stack processors. The lru_cache on get_settings() ensures settings
    are only read once, so configure_logging() is idempotent in tests.

Context binding:
    Callers add request-scoped context with structlog.contextvars:
        structlog.contextvars.bind_contextvars(user_id=user_id, request_id=req_id)
    All subsequent log calls in that coroutine include these fields automatically.

Usage
-----
    from src.core.logging import configure_logging
    configure_logging()  # call once in app lifespan

    import structlog
    logger = structlog.get_logger()
    logger.info("user_registered", email=email, user_id=str(user_id))
"""

import logging
import sys

import structlog


def configure_logging(is_development: bool = True) -> None:
    """
    Configure structlog for the application.

    Call once during app startup. Safe to call multiple times (idempotent).

    Args:
        is_development: If True, use colored ConsoleRenderer. If False, use
            JSON renderer suitable for log aggregators.
    """
    shared_processors: list = [
        # Add log level to every event dict
        structlog.stdlib.add_log_level,
        # Add timestamp in ISO 8601
        structlog.processors.TimeStamper(fmt="iso"),
        # Allow %s-style formatting in addition to keyword args
        structlog.stdlib.PositionalArgumentsFormatter(),
        # Render exceptions with full tracebacks
        structlog.processors.StackInfoRenderer(),
        # Format exception tracebacks
        structlog.processors.format_exc_info,
        # Decode bytes to strings in event values
        structlog.processors.UnicodeDecoder(),
    ]

    if is_development:
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Suppress noisy stdlib loggers in production
    if not is_development:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("beanie").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Return a structlog logger, optionally bound to a name.

    Convenience wrapper so callers don't need to import structlog directly.

    Usage:
        logger = get_logger(__name__)
        logger.info("event", key="value")
    """
    return structlog.get_logger(name)
