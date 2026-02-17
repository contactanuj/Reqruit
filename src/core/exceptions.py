"""
Custom exception hierarchy for the application.

Design decisions
----------------
Why custom exceptions (not raw HTTPException everywhere):
    FastAPI's HTTPException is tied to HTTP — it carries a status_code and
    detail string. But exceptions can originate deep in services, repositories,
    or LLM calls where HTTP concepts do not belong. A service should raise
    NotFoundError("Job not found"), not HTTPException(status_code=404).

    The API layer catches these domain exceptions and maps them to HTTP
    responses via FastAPI exception handlers (registered in src/api/main.py).
    This keeps HTTP concerns at the API boundary and business logic clean.

    Alternative: raise HTTPException directly from services. Works for small
    projects but couples business logic to HTTP — makes it harder to reuse
    services in CLI tools, background workers, or tests.

Why a base AppError with status_code and error_code:
    - status_code: used by the API exception handler to set the HTTP status.
    - error_code: a machine-readable string (e.g., "AUTH_TOKEN_EXPIRED") that
      frontends and API consumers can switch on without parsing error messages.
    - detail: a human-readable message for debugging and user-facing errors.

    This three-field pattern is common in production APIs (Stripe, GitHub,
    Twilio) and makes errors easy to handle programmatically.

Usage
-----
In a service:
    raise NotFoundError("Job", job_id)      # -> 404, JOB_NOT_FOUND

In the API layer (automatically via exception handlers in main.py):
    {"error_code": "JOB_NOT_FOUND", "detail": "Job abc123 not found"}
"""


class AppError(Exception):
    """
    Base exception for all application errors.

    All custom exceptions inherit from this class. The API layer registers
    a single handler for AppError that converts it to a JSON response
    with the appropriate HTTP status code.

    Attributes:
        status_code: HTTP status code for the API response.
        detail: Human-readable error message.
        error_code: Machine-readable error identifier (UPPER_SNAKE_CASE).
    """

    def __init__(
        self,
        detail: str = "An unexpected error occurred",
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
    ) -> None:
        self.detail = detail
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.detail)


# ---------------------------------------------------------------------------
# Authentication & Authorization
# ---------------------------------------------------------------------------


class AuthenticationError(AppError):
    """
    Raised when authentication fails: invalid credentials, expired tokens,
    malformed JWT, etc.

    Maps to HTTP 401 Unauthorized.
    """

    def __init__(
        self,
        detail: str = "Authentication failed",
        error_code: str = "AUTH_FAILED",
    ) -> None:
        super().__init__(detail=detail, status_code=401, error_code=error_code)


class AuthorizationError(AppError):
    """
    Raised when a user is authenticated but lacks permission for the action.

    Maps to HTTP 403 Forbidden. Distinct from AuthenticationError (401):
    - 401 = "Who are you?" (identity unknown)
    - 403 = "I know who you are, but you can't do that" (insufficient privileges)
    """

    def __init__(
        self,
        detail: str = "Insufficient permissions",
        error_code: str = "FORBIDDEN",
    ) -> None:
        super().__init__(detail=detail, status_code=403, error_code=error_code)


# ---------------------------------------------------------------------------
# Resource Errors
# ---------------------------------------------------------------------------


class NotFoundError(AppError):
    """
    Raised when a requested resource does not exist.

    Maps to HTTP 404 Not Found. Accepts a resource type and optional ID
    for consistent error messages across the app.
    """

    def __init__(
        self,
        resource: str = "Resource",
        resource_id: str | None = None,
    ) -> None:
        detail = f"{resource} not found" if not resource_id else (
            f"{resource} {resource_id} not found"
        )
        error_code = f"{resource.upper().replace(' ', '_')}_NOT_FOUND"
        super().__init__(detail=detail, status_code=404, error_code=error_code)


class ConflictError(AppError):
    """
    Raised when an operation conflicts with existing state.

    Maps to HTTP 409 Conflict. Examples: duplicate email on registration,
    applying to a job that already has an active application.
    """

    def __init__(
        self,
        detail: str = "Resource conflict",
        error_code: str = "CONFLICT",
    ) -> None:
        super().__init__(detail=detail, status_code=409, error_code=error_code)


# ---------------------------------------------------------------------------
# Validation Errors
# ---------------------------------------------------------------------------


class BusinessValidationError(AppError):
    """
    Raised when business logic validation fails.

    Maps to HTTP 422 Unprocessable Entity. This is distinct from Pydantic's
    ValidationError (which FastAPI handles automatically for malformed requests).

    Use this for rules that live in services, not schemas:
        - "Cannot apply to a job older than 30 days"
        - "Resume must have at least one work experience entry"
        - "Monthly LLM budget exceeded"
    """

    def __init__(
        self,
        detail: str = "Validation failed",
        error_code: str = "VALIDATION_FAILED",
    ) -> None:
        super().__init__(detail=detail, status_code=422, error_code=error_code)


# ---------------------------------------------------------------------------
# LLM / AI Errors
# ---------------------------------------------------------------------------


class LLMProviderError(AppError):
    """
    Raised when an LLM API call fails.

    Maps to HTTP 502 Bad Gateway — the upstream LLM provider returned an
    error or timed out. The circuit breaker catches these to decide whether
    to mark a provider as unhealthy.
    """

    def __init__(
        self,
        detail: str = "LLM provider error",
        provider: str = "unknown",
        error_code: str = "LLM_PROVIDER_ERROR",
    ) -> None:
        self.provider = provider
        super().__init__(
            detail=f"[{provider}] {detail}",
            status_code=502,
            error_code=error_code,
        )


class RateLimitError(AppError):
    """
    Raised when a rate limit or budget is exceeded.

    Maps to HTTP 429 Too Many Requests. Two scenarios:
    1. LLM provider rate limit (retry after cooldown)
    2. User's monthly cost budget exceeded (no retry — user action needed)
    """

    def __init__(
        self,
        detail: str = "Rate limit exceeded",
        error_code: str = "RATE_LIMITED",
    ) -> None:
        super().__init__(detail=detail, status_code=429, error_code=error_code)


# ---------------------------------------------------------------------------
# Database Errors
# ---------------------------------------------------------------------------


class DatabaseError(AppError):
    """
    Raised when a database operation fails unexpectedly.

    Maps to HTTP 500 Internal Server Error. Wraps MongoDB/Weaviate errors
    so services do not leak database-specific exceptions to callers.
    """

    def __init__(
        self,
        detail: str = "Database operation failed",
        error_code: str = "DATABASE_ERROR",
    ) -> None:
        super().__init__(detail=detail, status_code=500, error_code=error_code)


class VectorSearchError(AppError):
    """
    Raised when a Weaviate vector search operation fails.

    Maps to HTTP 500 Internal Server Error. Distinct from DatabaseError
    because vector search failures have different retry characteristics
    and the error context (collection name, query type) differs from
    document database errors.
    """

    def __init__(
        self,
        detail: str = "Vector search failed",
        error_code: str = "VECTOR_SEARCH_ERROR",
    ) -> None:
        super().__init__(detail=detail, status_code=500, error_code=error_code)


class EmbeddingError(AppError):
    """
    Raised when embedding generation fails.

    Maps to HTTP 500 Internal Server Error. The embedding model runs locally
    (BGE-small-en-v1.5), so failures are typically due to model loading
    issues or unexpected input (empty text, encoding errors).
    """

    def __init__(
        self,
        detail: str = "Embedding generation failed",
        error_code: str = "EMBEDDING_ERROR",
    ) -> None:
        super().__init__(detail=detail, status_code=500, error_code=error_code)
