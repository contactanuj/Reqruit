"""
Circuit breaker for LLM provider resilience.

The circuit breaker prevents repeated calls to a provider that is known to be
failing. Instead of waiting for timeouts on every request, the breaker "opens"
after a threshold of consecutive failures, blocking further attempts until a
recovery timeout has elapsed.

Design decisions
----------------
Why per-provider circuits (not per-model):
    Provider outages affect all models from that provider. If Anthropic's API
    is down, both Claude Sonnet and Claude Haiku will fail. Tracking at the
    provider level is the right granularity — one open circuit blocks all
    models from that provider, and one successful probe re-enables them all.

Why in-memory state (not persisted to MongoDB):
    Provider outages are transient — typically minutes, rarely hours. The
    circuit state is only meaningful for the current server process. If the
    server restarts, all circuits reset to CLOSED, which is the correct
    starting state (the provider might have recovered during our downtime).

    Persisting circuit state would add write latency to every LLM call and
    complexity around stale state after restarts.

Why the standard three-state pattern (CLOSED/OPEN/HALF_OPEN):
    This is the industry-standard circuit breaker pattern (originally from
    Michael Nygard's "Release It!"). It handles the three phases of failure
    management:
    1. CLOSED: everything is fine, let requests through.
    2. OPEN: provider is broken, block requests to avoid wasted timeouts.
    3. HALF_OPEN: enough time has passed, try one request to see if the
       provider has recovered.

    The alternative (just retry with exponential backoff) keeps hitting the
    failed provider, wasting time on every request until it recovers. The
    circuit breaker skips the provider entirely during the outage window.

Usage
-----
The ModelManager creates one CircuitBreaker and uses it to check provider
availability before making LLM calls:

    breaker = CircuitBreaker()

    if breaker.is_available(ProviderName.ANTHROPIC):
        try:
            result = await model.ainvoke(messages)
            breaker.record_success(ProviderName.ANTHROPIC)
        except Exception:
            breaker.record_failure(ProviderName.ANTHROPIC)
"""

import time

import structlog

from src.llm.models import CircuitState, ProviderName

logger = structlog.get_logger()

# Default thresholds. These are conservative — 3 consecutive failures before
# opening, 60 seconds before probing. For a single-user app with multiple
# providers and fallbacks, false positives (opening too early) are worse than
# false negatives (opening too late), because we have fallback providers.
DEFAULT_FAILURE_THRESHOLD = 3
DEFAULT_RECOVERY_TIMEOUT = 60.0  # seconds


class ProviderCircuit:
    """
    Health state for a single LLM provider.

    Tracks consecutive failures and manages state transitions between
    CLOSED, OPEN, and HALF_OPEN. Thread-safe for single-process async
    use (no concurrent mutation in asyncio's cooperative model).

    Attributes:
        state: Current circuit state.
        failure_count: Consecutive failures since last success or reset.
        last_failure_time: Monotonic timestamp of the most recent failure.
            Used to determine when the recovery timeout has elapsed.
        failure_threshold: How many consecutive failures trigger OPEN.
        recovery_timeout: Seconds to wait before transitioning from OPEN
            to HALF_OPEN for a recovery probe.
    """

    def __init__(
        self,
        failure_threshold: int = DEFAULT_FAILURE_THRESHOLD,
        recovery_timeout: float = DEFAULT_RECOVERY_TIMEOUT,
    ) -> None:
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

    def is_available(self) -> bool:
        """
        Check whether this provider should receive requests.

        CLOSED: always available.
        OPEN: available only if recovery_timeout has elapsed, in which case
              the state transitions to HALF_OPEN (one probe allowed).
        HALF_OPEN: available (the probe request is in flight).
        """
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if self.last_failure_time is None:
                return False
            elapsed = time.monotonic() - self.last_failure_time
            if elapsed >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                return True
            return False

        # HALF_OPEN: allow exactly one probe request.
        return True

    def record_success(self) -> None:
        """
        Record a successful response from this provider.

        Resets the circuit to CLOSED regardless of current state.
        In HALF_OPEN, this confirms the provider has recovered.
        """
        previous = self.state
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None

        if previous != CircuitState.CLOSED:
            logger.info(
                "circuit_recovered",
                previous_state=previous.value,
            )

    def record_failure(self) -> None:
        """
        Record a failed response from this provider.

        In CLOSED: increments failure_count. Opens the circuit after
            failure_threshold consecutive failures.
        In HALF_OPEN: the probe failed — back to OPEN immediately.
        In OPEN: should not happen (requests are blocked), but handles
            it gracefully by staying OPEN.
        """
        self.failure_count += 1
        self.last_failure_time = time.monotonic()

        if self.state == CircuitState.HALF_OPEN:
            # Probe failed — provider is still unhealthy.
            self.state = CircuitState.OPEN
            logger.warning("circuit_probe_failed")

        elif (
            self.state == CircuitState.CLOSED
            and self.failure_count >= self.failure_threshold
        ):
            self.state = CircuitState.OPEN
            logger.warning(
                "circuit_opened",
                failure_count=self.failure_count,
                threshold=self.failure_threshold,
            )


class CircuitBreaker:
    """
    Manages per-provider circuit breakers.

    Creates a ProviderCircuit for each provider on first access. The
    ModelManager uses this class to check availability before selecting
    a model and to report success/failure after each LLM call.
    """

    def __init__(
        self,
        failure_threshold: int = DEFAULT_FAILURE_THRESHOLD,
        recovery_timeout: float = DEFAULT_RECOVERY_TIMEOUT,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._circuits: dict[ProviderName, ProviderCircuit] = {}

    def _get_circuit(self, provider: ProviderName) -> ProviderCircuit:
        """Get or create the circuit for a provider."""
        if provider not in self._circuits:
            self._circuits[provider] = ProviderCircuit(
                failure_threshold=self._failure_threshold,
                recovery_timeout=self._recovery_timeout,
            )
        return self._circuits[provider]

    def is_available(self, provider: ProviderName) -> bool:
        """Check whether a provider should receive requests."""
        return self._get_circuit(provider).is_available()

    def record_success(self, provider: ProviderName) -> None:
        """Record a successful response from a provider."""
        self._get_circuit(provider).record_success()

    def record_failure(self, provider: ProviderName) -> None:
        """Record a failed response from a provider."""
        logger.warning("provider_failure", provider=provider.value)
        self._get_circuit(provider).record_failure()

    def get_status(self) -> dict[str, str]:
        """
        Return current state of all tracked circuits.

        Useful for health check endpoints and debugging. Returns a dict
        mapping provider names to their circuit state strings.
        """
        return {
            provider.value: circuit.state.value
            for provider, circuit in self._circuits.items()
        }
