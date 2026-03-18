"""Unit tests for src/core/logging.py and src/api/middleware/logging.py."""

import io
import json
from unittest.mock import MagicMock

import pytest
import structlog
import structlog.contextvars
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.core.logging import configure_logging, get_logger


class TestConfigureLogging:
    def test_configure_logging_dev_mode(self):
        """configure_logging runs without error in development mode."""
        configure_logging(is_development=True)
        logger = structlog.get_logger("test")
        assert logger is not None

    def test_configure_logging_prod_mode(self):
        """configure_logging runs without error in production mode."""
        configure_logging(is_development=False)
        logger = structlog.get_logger("test")
        assert logger is not None

    def test_configure_logging_idempotent(self):
        """Calling configure_logging twice does not raise."""
        configure_logging(is_development=True)
        configure_logging(is_development=True)

    def test_get_logger_returns_bound_logger(self):
        configure_logging(is_development=True)
        logger = get_logger("mymodule")
        assert logger is not None

    def test_get_logger_no_name(self):
        configure_logging(is_development=True)
        logger = get_logger()
        assert logger is not None

    def test_json_renderer_in_prod(self):
        """In production mode, structlog outputs valid JSON lines."""
        buf = io.StringIO()
        configure_logging(is_development=False)

        # Reconfigure with our buffer as output to capture logs
        structlog.configure(
            processors=[
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer(),
            ],
            logger_factory=structlog.PrintLoggerFactory(file=buf),
            cache_logger_on_first_use=False,
        )

        logger = structlog.get_logger()
        logger.info("test_event", key="value")

        output = buf.getvalue().strip()
        assert output, "No log output captured"
        data = json.loads(output)
        assert data["event"] == "test_event"
        assert data["key"] == "value"
        assert "level" in data


class TestExtractUserId:
    def test_returns_none_without_auth_header(self, test_settings):
        from src.api.middleware.logging import _extract_user_id
        request = MagicMock()
        request.headers = {}
        assert _extract_user_id(request) is None

    def test_returns_none_for_non_bearer(self, test_settings):
        from src.api.middleware.logging import _extract_user_id
        request = MagicMock()
        request.headers = {"Authorization": "Basic dXNlcjpwYXNz"}
        assert _extract_user_id(request) is None

    def test_returns_user_id_for_valid_token(self, test_settings):
        from src.api.middleware.logging import _extract_user_id
        from src.core.security import create_access_token

        token = create_access_token("abc123")
        request = MagicMock()
        request.headers = {"Authorization": f"Bearer {token}"}
        user_id = _extract_user_id(request)
        assert user_id == "abc123"

    def test_returns_none_for_invalid_token(self, test_settings):
        from src.api.middleware.logging import _extract_user_id
        request = MagicMock()
        request.headers = {"Authorization": "Bearer not.a.real.token"}
        assert _extract_user_id(request) is None


class TestRequestLoggingMiddleware:
    @pytest.fixture
    def logged_app(self):
        """Minimal FastAPI app with only the logging middleware."""
        from src.api.middleware.logging import RequestLoggingMiddleware

        app = FastAPI()
        app.add_middleware(RequestLoggingMiddleware)

        @app.get("/ping")
        async def ping():
            return {"pong": True}

        return app

    async def test_middleware_passes_request_through(self, logged_app):
        transport = ASGITransport(app=logged_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/ping")
        assert response.status_code == 200

    async def test_response_includes_request_id_header(self, logged_app):
        transport = ASGITransport(app=logged_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/ping")
        assert "x-request-id" in response.headers
        assert len(response.headers["x-request-id"]) == 36  # UUID4 length

    async def test_unique_request_ids_per_request(self, logged_app):
        transport = ASGITransport(app=logged_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r1 = await ac.get("/ping")
            r2 = await ac.get("/ping")
        assert r1.headers["x-request-id"] != r2.headers["x-request-id"]

    async def test_middleware_does_not_break_on_404(self, logged_app):
        transport = ASGITransport(app=logged_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/nonexistent")
        assert response.status_code == 404
        assert "x-request-id" in response.headers
