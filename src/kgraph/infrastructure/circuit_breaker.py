"""Simple async circuit breaker for external service calls.

Implements the three-state circuit breaker pattern:
  CLOSED  — requests flow through normally
  OPEN    — requests fail fast without calling the service
  HALF_OPEN — one probe request is allowed through to test recovery
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import TypeVar

from kgraph.domain.errors import ServiceUnavailableError
from kgraph.infrastructure.logging import get_logger

T = TypeVar("T")

_log = get_logger(__name__)


class CircuitState(Enum):
    """States of the circuit breaker."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Async circuit breaker that wraps external service calls.

    Args:
        name: Identifier for logging and error messages.
        failure_threshold: Consecutive failures before opening the circuit.
        recovery_timeout: Seconds to wait in OPEN state before probing.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
    ) -> None:
        self._name = name
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at: float = 0.0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    async def call(self, func: Callable[..., Awaitable[T]], *args: object, **kwargs: object) -> T:
        """Execute func through the circuit breaker.

        Raises:
            ServiceUnavailableError: When the circuit is OPEN.
        """
        async with self._lock:
            if self._state == CircuitState.OPEN:
                if time.monotonic() - self._opened_at >= self._recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    _log.info("circuit_breaker.half_open", circuit=self._name)
                else:
                    raise ServiceUnavailableError(
                        f"Circuit '{self._name}' is OPEN — service unavailable"
                    )

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as exc:
            await self._on_failure(exc)
            raise

    async def _on_success(self) -> None:
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                _log.info("circuit_breaker.closed", circuit=self._name)
            self._state = CircuitState.CLOSED
            self._failure_count = 0

    async def _on_failure(self, exc: Exception) -> None:
        async with self._lock:
            self._failure_count += 1
            _log.warning(
                "circuit_breaker.failure",
                circuit=self._name,
                failure_count=self._failure_count,
                error=str(exc),
            )
            if self._failure_count >= self._failure_threshold:
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()
                _log.error(
                    "circuit_breaker.opened",
                    circuit=self._name,
                    failure_threshold=self._failure_threshold,
                )
