"""
Shared test fixtures for the entire test suite.

pytest-asyncio configuration
-----------------------------
We set asyncio_mode = "auto" in pyproject.toml so all async test functions
are automatically recognized without needing @pytest.mark.asyncio on each one.
This reduces boilerplate across the test suite.

Fixtures defined here are available to all tests in both tests/unit/ and
tests/integration/ without explicit imports.

Why mock DB connections in the client fixture
---------------------------------------------
The FastAPI lifespan calls connect_mongodb() and connect_weaviate() on startup.
Without mocking these, every test that uses the HTTP client would need running
MongoDB and Weaviate instances — that is integration testing, not unit testing.

By patching the connection functions, the lifespan runs successfully without
external services. The health check endpoint still works because it only reads
settings, not database state.
"""

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import create_app
from src.core.config import Settings, get_settings


def _get_test_settings() -> Settings:
    """Return a Settings instance configured for testing."""
    # Override specific values for the test environment.
    # Using a distinct database name prevents test runs from touching dev data.
    import os

    os.environ["APP_ENV"] = "testing"
    os.environ["APP_NAME"] = "job-hunt-test"
    os.environ["DEBUG"] = "true"
    os.environ["MONGODB_DATABASE"] = "job_hunt_test"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"

    # Clear the settings cache so new env vars are picked up
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture
def test_settings() -> Settings:
    """Provide test-specific settings."""
    return _get_test_settings()


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """
    Provide an async HTTP test client with mocked external dependencies.

    Uses httpx.AsyncClient with ASGI transport — sends requests directly
    to the FastAPI app without starting a real server. This is faster and
    more reliable than TestClient (which uses requests, a sync library).

    Database connections (MongoDB + Weaviate) and the ModelManager are
    mocked because unit tests should not depend on external services or
    LLM API keys. The lifespan still runs — it just calls no-op mocks
    instead of real connection/init functions.

    Note: close_mongodb and the ModelManager lifecycle functions are
    synchronous. The DB connect/close_weaviate functions are async.

    Usage in tests:
        async def test_health(client):
            response = await client.get("/health")
            assert response.status_code == 200
    """
    _get_test_settings()

    with (
        patch("src.api.main.connect_mongodb", new_callable=AsyncMock),
        patch("src.api.main.connect_weaviate", new_callable=AsyncMock),
        patch("src.api.main.close_mongodb"),
        patch("src.api.main.close_weaviate", new_callable=AsyncMock),
        patch("src.api.main.init_embeddings"),
        patch("src.api.main.close_embeddings"),
        patch("src.api.main.init_model_manager"),
        patch("src.api.main.close_model_manager"),
        patch("src.api.main.init_checkpointer"),
        patch("src.api.main.close_checkpointer"),
    ):
        application = create_app()
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
