"""
Base class for external API clients with httpx and simple circuit breaker.

All third-party integration clients (Gmail, Calendar, etc.) extend this class
to get consistent HTTP handling, timeout defaults, and failure tracking.
"""

import time

import httpx
import structlog

logger = structlog.get_logger()

DEFAULT_TIMEOUT = 30.0
DEFAULT_FAILURE_THRESHOLD = 3
DEFAULT_RECOVERY_TIMEOUT = 60.0


class ExternalAPIError(Exception):
    """Raised when an external API returns an error response."""

    def __init__(self, status_code: int, detail: str, provider: str = "unknown") -> None:
        self.status_code = status_code
        self.detail = detail
        self.provider = provider
        super().__init__(f"[{provider}] {status_code}: {detail}")


class BaseExternalClient:
    """
    Base HTTP client for external service integrations.

    Provides an httpx.AsyncClient with configurable timeout and a
    lightweight circuit breaker to avoid hammering failing services.
    """

    def __init__(
        self,
        base_url: str = "",
        timeout: float = DEFAULT_TIMEOUT,
        failure_threshold: int = DEFAULT_FAILURE_THRESHOLD,
        recovery_timeout: float = DEFAULT_RECOVERY_TIMEOUT,
    ) -> None:
        self._base_url = base_url
        self._timeout = timeout
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._failure_count = 0
        self._last_failure_time: float | None = None
        self._circuit_open = False

    def _check_circuit(self) -> None:
        """Raise if the circuit is open and recovery timeout hasn't elapsed."""
        if not self._circuit_open:
            return
        if self._last_failure_time is None:
            return
        elapsed = time.monotonic() - self._last_failure_time
        if elapsed >= self._recovery_timeout:
            self._circuit_open = False
            self._failure_count = 0
            logger.info("external_circuit_recovered", client=type(self).__name__)
        else:
            raise ExternalAPIError(
                status_code=503,
                detail="Circuit breaker open — service temporarily unavailable",
                provider=type(self).__name__,
            )

    def _record_success(self) -> None:
        self._failure_count = 0
        self._circuit_open = False

    def _record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self._failure_threshold:
            self._circuit_open = True
            logger.warning(
                "external_circuit_opened",
                client=type(self).__name__,
                failure_count=self._failure_count,
            )

    async def _request(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> httpx.Response:
        """Make an HTTP request with circuit breaker and error handling."""
        self._check_circuit()
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.request(method, url, **kwargs)
            self._record_success()
            return response
        except httpx.HTTPError as exc:
            self._record_failure()
            raise ExternalAPIError(
                status_code=503,
                detail=str(exc),
                provider=type(self).__name__,
            ) from exc
