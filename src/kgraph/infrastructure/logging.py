"""Structured logging configuration for kgraph.

Configures structlog with JSON output in production and pretty-printed
console output when verbose mode is enabled.
"""

from __future__ import annotations

import structlog


def configure_logging(verbose: bool = False) -> None:
    """Configure structlog for the kgraph process.

    Args:
        verbose: When True, use human-readable console output.
                 When False (default), emit JSON for log aggregation.
    """
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if verbose:
        processors: list[structlog.types.Processor] = [
            *shared_processors,
            structlog.dev.ConsoleRenderer(),
        ]
    else:
        processors = [
            *shared_processors,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    level = structlog.stdlib.NAME_TO_LEVEL["debug" if verbose else "info"]
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a bound logger namespaced to the given module name."""
    return structlog.get_logger(name)
