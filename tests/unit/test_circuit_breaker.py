"""Unit tests for CircuitBreaker — state transitions and fast-fail behavior."""

from __future__ import annotations

import pytest

from kgraph.domain.errors import ServiceUnavailableError
from kgraph.infrastructure.circuit_breaker import CircuitBreaker, CircuitState


async def _always_succeed() -> str:
    return "ok"


async def _always_fail() -> None:
    raise RuntimeError("downstream failure")


class TestCircuitBreakerClosed:
    async def test_initial_state_is_closed(self) -> None:
        cb = CircuitBreaker(name="test", failure_threshold=3)
        assert cb.state == CircuitState.CLOSED

    async def test_successful_call_keeps_circuit_closed(self) -> None:
        cb = CircuitBreaker(name="test", failure_threshold=3)
        result = await cb.call(_always_succeed)
        assert result == "ok"
        assert cb.state == CircuitState.CLOSED

    async def test_single_failure_does_not_open_circuit(self) -> None:
        cb = CircuitBreaker(name="test", failure_threshold=3)
        with pytest.raises(RuntimeError):
            await cb.call(_always_fail)
        assert cb.state == CircuitState.CLOSED

    async def test_failures_below_threshold_keep_circuit_closed(self) -> None:
        cb = CircuitBreaker(name="test", failure_threshold=3)
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(_always_fail)
        assert cb.state == CircuitState.CLOSED


class TestCircuitBreakerOpen:
    async def test_failures_at_threshold_open_circuit(self) -> None:
        cb = CircuitBreaker(name="test", failure_threshold=3)
        for _ in range(3):
            with pytest.raises(RuntimeError):
                await cb.call(_always_fail)
        assert cb.state == CircuitState.OPEN

    async def test_open_circuit_raises_service_unavailable(self) -> None:
        cb = CircuitBreaker(name="test", failure_threshold=2)
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(_always_fail)

        with pytest.raises(ServiceUnavailableError, match="OPEN"):
            await cb.call(_always_succeed)

    async def test_open_circuit_does_not_call_function(self) -> None:
        call_count = 0

        async def tracked() -> str:
            nonlocal call_count
            call_count += 1
            return "ok"

        cb = CircuitBreaker(name="test", failure_threshold=1)
        with pytest.raises(RuntimeError):
            await cb.call(_always_fail)

        with pytest.raises(ServiceUnavailableError):
            await cb.call(tracked)

        assert call_count == 0


class TestCircuitBreakerHalfOpen:
    async def test_open_circuit_transitions_to_half_open_after_timeout(self) -> None:
        cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout=0.0)
        with pytest.raises(RuntimeError):
            await cb.call(_always_fail)
        assert cb.state == CircuitState.OPEN

        result = await cb.call(_always_succeed)
        assert result == "ok"
        assert cb.state == CircuitState.CLOSED

    async def test_half_open_success_closes_circuit(self) -> None:
        cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout=0.0)
        with pytest.raises(RuntimeError):
            await cb.call(_always_fail)

        await cb.call(_always_succeed)
        assert cb.state == CircuitState.CLOSED
        assert cb._failure_count == 0

    async def test_half_open_failure_reopens_circuit(self) -> None:
        cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout=0.0)
        with pytest.raises(RuntimeError):
            await cb.call(_always_fail)

        with pytest.raises(RuntimeError):
            await cb.call(_always_fail)

        assert cb.state == CircuitState.OPEN

    async def test_success_after_failures_resets_failure_count(self) -> None:
        cb = CircuitBreaker(name="test", failure_threshold=5)
        for _ in range(3):
            with pytest.raises(RuntimeError):
                await cb.call(_always_fail)

        await cb.call(_always_succeed)
        assert cb._failure_count == 0
        assert cb.state == CircuitState.CLOSED
