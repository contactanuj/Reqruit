"""
Tests for the circuit breaker resilience mechanism.

The circuit breaker is a state machine with three states: CLOSED, OPEN,
HALF_OPEN. These tests verify every state transition and the time-based
recovery logic.
"""

import time

from src.llm.circuit_breaker import (
    CircuitBreaker,
    ProviderCircuit,
)
from src.llm.models import CircuitState, ProviderName


class TestProviderCircuit:
    """Test the single-provider circuit state machine."""

    def test_starts_closed_and_available(self):
        circuit = ProviderCircuit()
        assert circuit.state == CircuitState.CLOSED
        assert circuit.is_available() is True
        assert circuit.failure_count == 0

    def test_stays_available_under_threshold(self):
        """Failures below the threshold do not open the circuit."""
        circuit = ProviderCircuit(failure_threshold=3)
        circuit.record_failure()
        circuit.record_failure()
        assert circuit.state == CircuitState.CLOSED
        assert circuit.failure_count == 2
        assert circuit.is_available() is True

    def test_opens_after_reaching_failure_threshold(self):
        """Consecutive failures at the threshold trigger OPEN state."""
        circuit = ProviderCircuit(failure_threshold=3)
        circuit.record_failure()
        circuit.record_failure()
        circuit.record_failure()
        assert circuit.state == CircuitState.OPEN
        assert circuit.failure_count == 3

    def test_open_circuit_is_unavailable(self):
        """An OPEN circuit blocks requests."""
        circuit = ProviderCircuit(failure_threshold=1)
        circuit.record_failure()
        assert circuit.state == CircuitState.OPEN
        assert circuit.is_available() is False

    def test_open_recovers_to_half_open_after_timeout(self):
        """After recovery_timeout, an OPEN circuit transitions to HALF_OPEN."""
        circuit = ProviderCircuit(failure_threshold=1, recovery_timeout=0.1)
        circuit.record_failure()
        assert circuit.state == CircuitState.OPEN

        # Simulate time passing beyond the recovery timeout.
        circuit.last_failure_time = time.monotonic() - 0.2
        assert circuit.is_available() is True
        assert circuit.state == CircuitState.HALF_OPEN

    def test_open_stays_open_before_timeout(self):
        """Before recovery_timeout, an OPEN circuit stays OPEN."""
        circuit = ProviderCircuit(failure_threshold=1, recovery_timeout=60.0)
        circuit.record_failure()
        assert circuit.is_available() is False
        assert circuit.state == CircuitState.OPEN

    def test_half_open_allows_one_probe(self):
        """A HALF_OPEN circuit is available for exactly one probe request."""
        circuit = ProviderCircuit(failure_threshold=1, recovery_timeout=0.0)
        circuit.record_failure()
        # Immediately past timeout (recovery_timeout=0.0).
        assert circuit.is_available() is True
        assert circuit.state == CircuitState.HALF_OPEN

    def test_success_in_half_open_resets_to_closed(self):
        """A successful probe in HALF_OPEN confirms recovery -> CLOSED."""
        circuit = ProviderCircuit(failure_threshold=1, recovery_timeout=0.0)
        circuit.record_failure()
        circuit.is_available()  # Transitions to HALF_OPEN
        assert circuit.state == CircuitState.HALF_OPEN

        circuit.record_success()
        assert circuit.state == CircuitState.CLOSED
        assert circuit.failure_count == 0
        assert circuit.last_failure_time is None

    def test_failure_in_half_open_reopens(self):
        """A failed probe in HALF_OPEN sends the circuit back to OPEN."""
        circuit = ProviderCircuit(failure_threshold=1, recovery_timeout=0.0)
        circuit.record_failure()
        circuit.is_available()  # Transitions to HALF_OPEN
        assert circuit.state == CircuitState.HALF_OPEN

        circuit.record_failure()
        assert circuit.state == CircuitState.OPEN

    def test_success_resets_failure_count(self):
        """A success in CLOSED state resets the failure counter."""
        circuit = ProviderCircuit(failure_threshold=3)
        circuit.record_failure()
        circuit.record_failure()
        assert circuit.failure_count == 2

        circuit.record_success()
        assert circuit.failure_count == 0
        assert circuit.state == CircuitState.CLOSED


class TestCircuitBreaker:
    """Test the multi-provider circuit breaker manager."""

    def test_new_provider_starts_available(self):
        """First access to an unknown provider creates a CLOSED circuit."""
        breaker = CircuitBreaker()
        assert breaker.is_available(ProviderName.ANTHROPIC) is True

    def test_independent_provider_tracking(self):
        """Failures in one provider do not affect others."""
        breaker = CircuitBreaker(failure_threshold=1)
        breaker.record_failure(ProviderName.ANTHROPIC)

        assert breaker.is_available(ProviderName.ANTHROPIC) is False
        assert breaker.is_available(ProviderName.OPENAI) is True
        assert breaker.is_available(ProviderName.GROQ) is True

    def test_record_success_resets_provider(self):
        breaker = CircuitBreaker(failure_threshold=2)
        breaker.record_failure(ProviderName.OPENAI)
        breaker.record_failure(ProviderName.OPENAI)
        assert breaker.is_available(ProviderName.OPENAI) is False

        # Simulate recovery timeout passing.
        circuit = breaker._get_circuit(ProviderName.OPENAI)
        circuit.last_failure_time = time.monotonic() - 120
        assert breaker.is_available(ProviderName.OPENAI) is True  # HALF_OPEN

        breaker.record_success(ProviderName.OPENAI)
        assert breaker.is_available(ProviderName.OPENAI) is True  # CLOSED

    def test_get_status_returns_all_tracked_circuits(self):
        breaker = CircuitBreaker()
        # Access two providers to create their circuits.
        breaker.is_available(ProviderName.ANTHROPIC)
        breaker.is_available(ProviderName.GROQ)

        status = breaker.get_status()
        assert "anthropic" in status
        assert "groq" in status
        assert status["anthropic"] == "closed"
        assert status["groq"] == "closed"

    def test_get_status_reflects_open_circuit(self):
        breaker = CircuitBreaker(failure_threshold=1)
        breaker.record_failure(ProviderName.OPENAI)

        status = breaker.get_status()
        assert status["openai"] == "open"
