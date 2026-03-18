"""
Integration test fixtures.

Integration tests make real calls to MongoDB, Weaviate, and LLM APIs.
They are NEVER run in CI — only manually when a full environment is available.

Skipping strategy
-----------------
Every integration test is marked with @pytest.mark.integration.
If the required environment variables are missing, the test is skipped
automatically with a clear message. No test fails with an import error.

Running integration tests
-------------------------
    # Requires: MongoDB + Weaviate running, API keys in .env
    pytest tests/integration/ -v

    # Or run a single suite
    pytest tests/integration/test_auth_flow.py -v

Environment requirements
------------------------
    MONGODB_URL        - Running MongoDB instance
    ANTHROPIC_API_KEY  - For LLM call tests (optional per test)
    GROQ_API_KEY       - For free-tier LLM tests (optional per test)
"""

import os

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import create_app
from src.core.config import Settings, get_settings
from src.db.mongodb import close_mongodb, connect_mongodb

# ---------------------------------------------------------------------------
# pytest marks
# ---------------------------------------------------------------------------

def pytest_configure(config):
    """Register the 'integration' marker so -m integration works."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (require real services)",
    )


# ---------------------------------------------------------------------------
# Skip helpers
# ---------------------------------------------------------------------------

def _require_env(*var_names: str) -> pytest.MarkDecorator:
    """
    Skip the test if any of the required env vars are missing or empty.

    Usage:
        @_require_env("MONGODB_URL", "ANTHROPIC_API_KEY")
        async def test_cover_letter_agent(...):
            ...
    """
    missing = [v for v in var_names if not os.getenv(v)]
    reason = f"Missing environment variables: {', '.join(missing)}"
    return pytest.mark.skipif(bool(missing), reason=reason)


requires_mongodb = _require_env("MONGODB_URL")
requires_anthropic = _require_env("ANTHROPIC_API_KEY")
requires_groq = _require_env("GROQ_API_KEY")
requires_openai = _require_env("OPENAI_API_KEY")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def integration_settings() -> Settings:
    """
    Settings for integration tests.

    Uses a separate test database to avoid polluting development data.
    Reads real API keys from environment (loaded from .env in development).
    """
    os.environ.setdefault("MONGODB_DATABASE", "reqruit_integration_test")
    os.environ.setdefault("APP_ENV", "testing")
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture
async def db(integration_settings):
    """
    Connect to a real MongoDB instance for the duration of one test.

    Cleans up the test database after the test to prevent data accumulation.
    Skip automatically if MONGODB_URL is not set.
    """
    if not os.getenv("MONGODB_URL"):
        pytest.skip("MONGODB_URL not set — skipping integration test")

    await connect_mongodb(integration_settings)
    yield
    await close_mongodb()


@pytest.fixture
async def integration_client(integration_settings):
    """
    Full ASGI test client against a real app with real database connections.

    Only use when you need end-to-end HTTP testing with a real DB.
    For unit tests, use the `client` fixture from tests/conftest.py instead.
    """
    if not os.getenv("MONGODB_URL"):
        pytest.skip("MONGODB_URL not set — skipping integration test")

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
