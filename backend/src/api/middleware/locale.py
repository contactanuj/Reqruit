"""
Locale context injection middleware.

Reads the authenticated user's locale_profile and attaches market context
to request.state so downstream route handlers and agents can access it
without explicit wiring.

Design decisions
----------------
Why middleware (not a Depends() per endpoint):
    Locale context is a cross-cutting concern. With middleware, every
    authenticated request gets locale context automatically. Without it,
    each locale-aware endpoint would need an extra Depends() call,
    which is easy to forget and leads to inconsistency.

Why request.state (not a global or thread-local):
    request.state is the standard Starlette/FastAPI mechanism for passing
    data between middleware and route handlers. It is request-scoped and
    async-safe.

What gets attached:
    request.state.locale_profile: UserLocaleProfile dict (or None)
    request.state.primary_market: region code string (or None)
"""

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = structlog.get_logger()


class LocaleContextMiddleware(BaseHTTPMiddleware):
    """
    Inject locale context from the authenticated user into request.state.

    Runs after auth — if the user has a locale_profile, it is attached
    to request.state for downstream handlers. Non-authenticated requests
    get None values (middleware never blocks).
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Defaults — set before processing so they exist even if auth fails
        request.state.locale_profile = None
        request.state.primary_market = None

        # Try to extract locale from the current user
        # The user is set by get_current_user dependency, but middleware
        # runs before dependencies. We peek at the token and load the user
        # only for locale context — this is best-effort, never blocks.
        try:
            user = await self._get_user_from_token(request)
            if user and user.locale_profile:
                profile = user.locale_profile
                request.state.locale_profile = profile.model_dump()
                request.state.primary_market = profile.primary_market
        except Exception:
            # Locale injection is best-effort — never block a request
            pass

        return await call_next(request)

    async def _get_user_from_token(self, request: Request):
        """Extract user from JWT token without raising on failure."""
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None

        token = auth[len("Bearer "):]
        try:
            import jwt

            from src.core.config import get_settings
            from src.db.documents.user import User

            settings = get_settings()
            payload = jwt.decode(
                token,
                settings.auth.jwt_secret_key,
                algorithms=[settings.auth.jwt_algorithm],
            )

            user_id = payload.get("sub")
            if not user_id:
                return None

            from beanie import PydanticObjectId

            return await User.get(PydanticObjectId(user_id))
        except Exception:
            return None
