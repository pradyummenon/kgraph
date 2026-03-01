"""Structured logging configuration for kgraph.

Public entry point for logging setup. Delegates to the infrastructure
implementation so callers use a stable import path.

Usage:
    from kgraph.logging import configure_logging
    configure_logging(level="DEBUG")
"""

from __future__ import annotations

import sys

import structlog


def configure_logging(json_output: bool = False, level: str = "INFO") -> None:
    """Configure structlog for the kgraph process.

    Args:
        json_output: When True, emit JSON lines to stderr (production mode).
                     When False (default), use colored console output (dev mode).
        level: Minimum log level to emit. One of DEBUG, INFO, WARNING, ERROR.
    """
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if json_output:
        processors: list[structlog.types.Processor] = [
            *shared_processors,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        processors = [
            *shared_processors,
            structlog.dev.ConsoleRenderer(stream=sys.stderr),
        ]

    fallback = structlog.stdlib.NAME_TO_LEVEL["info"]
    numeric_level = structlog.stdlib.NAME_TO_LEVEL.get(level.lower(), fallback)
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )
