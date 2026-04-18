"""Structured logging configuration using *structlog*.

- **Production** (``environment != "development"``): JSON output for machine parsing.
- **Development**: Pretty-printed, coloured console output for readability.

Correlation IDs are attached to every log entry via the ``X-Request-ID``
header when available.
"""

from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(*, log_level: str = "INFO", environment: str = "development") -> None:
    """Set up *structlog* and stdlib logging for the application.

    Args:
        log_level: Root log level name (e.g. ``"INFO"``, ``"DEBUG"``).
        environment: ``"development"`` enables pretty-printing; anything
            else uses JSON rendering.
    """
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if environment == "development":
        renderer: structlog.types.Processor = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level.upper())

    # Suppress noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("azure.identity").setLevel(logging.WARNING)
    logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)


def sanitize_for_log(value: str) -> str:
    """Return a log-safe string by neutralizing line-break characters.

    Prevents log injection attacks by stripping carriage-return and
    newline characters from user-provided values before they are
    interpolated into log messages.
    """
    return value.replace("\r", "").replace("\n", "")


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a *structlog* bound logger.

    Args:
        name: Optional logger name. When omitted, ``None`` is passed through
            to ``structlog.get_logger()``.
    """
    return structlog.get_logger(name)
