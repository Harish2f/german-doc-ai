import pytest
from src.rag.circuit_breaker import CircuitState, CircuitBreaker


def test_circuit_breaker_starts():
    circuit_breaker = CircuitBreaker()
    assert circuit_breaker.state == CircuitState.CLOSED
  


def test_circuit_breaker_failure_count():
    circuit_breaker = CircuitBreaker()
    for _ in range(5):
        circuit_breaker.call_failed()
    assert circuit_breaker.state == CircuitState.OPEN
    assert not circuit_breaker.can_attempt()


def test_circuit_breaker_starts_closed():
    circuit_breaker = CircuitBreaker()
    assert circuit_breaker.state == CircuitState.CLOSED
    assert circuit_breaker.can_attempt()


def test_circuit_resets_after_success():
    circuit_breaker = CircuitBreaker()
    for _ in range(5):
        circuit_breaker.call_failed()
    assert circuit_breaker.state == CircuitState.OPEN
    circuit_breaker.call_succeeded()
    assert circuit_breaker.state == CircuitState.CLOSED
    assert circuit_breaker.failure_count == 0


