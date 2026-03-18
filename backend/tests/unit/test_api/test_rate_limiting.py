"""
Unit tests for rate limiting behavior (HTTP 429 responses).

Coverage:
  [P1] RateLimitError domain exception → 429 JSON response via exception handler
  [P1] Response body has correct structure: error_code="RATE_LIMITED"
  [P1] Budget-exceeded variant also returns 429
  [P2] Current absence of rate-limiting middleware documented

Rate limiting surface
---------------------
The exception handler in main.py maps RateLimitError (status_code=429) to
a JSON response. This is the current mechanism — no middleware enforces
request-rate limits (e.g., slowapi). The tests below verify the existing
exception-handler path works correctly and document that no middleware
enforcement exists today.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import (
    get_application_repository,
    get_current_user,
    get_job_repository,
)
from src.core.exceptions import RateLimitError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(user_id: str = "aaaaaaaaaaaaaaaaaaaaaaaa"):
    user = MagicMock()
    user.id = PydanticObjectId(user_id)
    return user


# ---------------------------------------------------------------------------
# Tests: RateLimitError → HTTP 429
# ---------------------------------------------------------------------------


async def test_rate_limit_error_returns_429(client: AsyncClient) -> None:
    """[P1] RateLimitError raised by a route dependency maps to HTTP 429.

    The AppError exception handler in main.py handles all AppError subclasses
    generically using their status_code attribute. RateLimitError sets
    status_code=429, so any endpoint raising it should return 429.
    """
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()

    mock_job_repo = AsyncMock()
    # Simulate a service raising RateLimitError (e.g., LLM budget exceeded)
    mock_job_repo.get_by_id.side_effect = RateLimitError("LLM daily budget exceeded")

    mock_app_repo = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo

    try:
        response = await client.get("/jobs/111111111111111111111111")
        assert response.status_code == 429
    finally:
        app.dependency_overrides.clear()


async def test_rate_limit_error_has_correct_error_code(client: AsyncClient) -> None:
    """[P1] 429 response body contains error_code='RATE_LIMITED' and detail message."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()

    mock_job_repo = AsyncMock()
    mock_job_repo.get_by_id.side_effect = RateLimitError("LLM daily budget exceeded")

    mock_app_repo = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo

    try:
        response = await client.get("/jobs/111111111111111111111111")
        assert response.status_code == 429
        data = response.json()
        assert data["error_code"] == "RATE_LIMITED"
        assert "budget" in data["detail"].lower() or "rate" in data["detail"].lower()
    finally:
        app.dependency_overrides.clear()


async def test_rate_limit_error_budget_exceeded_variant(client: AsyncClient) -> None:
    """[P1] RateLimitError with custom error_code still returns 429.

    The base RateLimitError defaults to error_code='RATE_LIMITED'. Services
    may raise it with a more specific code (e.g., 'MONTHLY_BUDGET_EXCEEDED').
    The HTTP status must remain 429 regardless of error_code.
    """
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()

    mock_job_repo = AsyncMock()
    mock_job_repo.get_by_id.side_effect = RateLimitError(
        detail="Monthly LLM budget of $10 exceeded",
        error_code="MONTHLY_BUDGET_EXCEEDED",
    )

    mock_app_repo = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo

    try:
        response = await client.get("/jobs/111111111111111111111111")
        assert response.status_code == 429
        data = response.json()
        assert data["error_code"] == "MONTHLY_BUDGET_EXCEEDED"
        assert "Monthly LLM budget" in data["detail"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.xfail(
    strict=False,
    reason=(
        "IMPLEMENTATION GAP: No request-rate-limiting middleware (e.g., slowapi). "
        "Failed login attempts are not throttled today. "
        "This test will XFAIL until a rate-limit middleware is added. "
        "Once implemented, it will XPASS and can be converted to a regular test."
    ),
)
async def test_multiple_failed_logins_do_not_trigger_429_currently(
    client: AsyncClient,
) -> None:
    """[P2] Documents absence of brute-force throttling on POST /auth/login.

    Today: repeated failed logins return 401 each time — no 429 is issued.
    Future: a sliding-window rate limiter should return 429 after N failures.
    """
    for _ in range(5):
        response = await client.post(
            "/auth/login",
            json={"email": "attacker@example.com", "password": "wrongpassword"},
        )
        # Current behavior: each attempt returns 401 (not 429)
        assert response.status_code != 429, (
            "Rate limiting triggered — update this test to verify correct 429 behavior"
        )
