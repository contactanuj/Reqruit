"""
Request/response logging middleware.

Design decisions
----------------
Why log in middleware (not in each endpoint):
    Middleware runs for every request without any per-endpoint code. Logging
    here guarantees uniform coverage: every request gets a log entry with
    path, method, status, latency, and user context — even 404s and 422s
    from Pydantic validation that never reach a route handler.

Why log user_id (not the full JWT):
    user_id is the minimal identifier needed to correlate logs to a user.
    The full JWT is a secret — logging it would be a security risk. We
    extract user_id by peeking at the Authorization header and decoding
    the token WITHOUT raising on failure (this is logging, not auth).

Why use structlog.contextvars.bind_contextvars:
    contextvars are coroutine-local in async Python. Binding user_id and
    request_id here means every subsequent log call in the same request
    coroutine automatically includes these fields — even deep in services
    and agents. No need to thread context through function arguments.

Log fields:
    method, path, status_code, duration_ms, user_id (if authenticated),
    request_id (uuid4, for correlation across services)
"""

import time
import uuid

import structlog
import structlog.contextvars
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = structlog.get_logger()


def _extract_user_id(request: Request) -> str | None:
    """
    Peek at the Authorization header and decode the user_id without raising.

    Returns None on any failure — this is logging context only, not auth.
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[len("Bearer "):]
    try:
        import jwt

        from src.core.config import get_settings  # noqa: PLC0415

        settings = get_settings()
        payload = jwt.decode(
            token,
            settings.auth.jwt_secret_key,
            algorithms=[settings.auth.jwt_algorithm],
        )
        return payload.get("sub")
    except Exception:
        return None


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Log every HTTP request with timing and user context.

    Emits two structlog events per request:
    - request_started: method + path + request_id, at the start
    - request_completed: adds status_code + duration_ms, at the end
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = str(uuid.uuid4())
        user_id = _extract_user_id(request)

        # Bind request-scoped context — flows to all downstream log calls
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            user_id=user_id,
        )

        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
        )

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = int((time.perf_counter() - start) * 1000)

        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        # Add request_id to response headers for client-side correlation
        response.headers["X-Request-Id"] = request_id
        return response
