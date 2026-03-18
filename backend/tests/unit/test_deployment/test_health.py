"""
Unit tests for /health and /health/ready endpoints.

Both endpoints are part of the deployment module:
  - /health      liveness probe (process alive?)
  - /health/ready readiness probe (dependencies reachable?)
"""

from unittest.mock import AsyncMock, patch


class TestLivenessCheck:
    async def test_health_returns_200(self, client):
        response = await client.get("/health")
        assert response.status_code == 200

    async def test_health_body_fields(self, client):
        response = await client.get("/health")
        body = response.json()
        assert body["status"] == "healthy"
        assert "app" in body
        assert "version" in body
        assert "environment" in body

    async def test_health_environment_is_testing(self, client):
        response = await client.get("/health")
        assert response.json()["environment"] == "testing"


class TestReadinessCheck:
    async def test_ready_200_when_all_deps_ok(self, client):
        with (
            patch(
                "src.api.main.get_mongodb_status",
                new_callable=AsyncMock,
                return_value={"status": "ok"},
            ),
            patch(
                "src.api.main.get_weaviate_status",
                new_callable=AsyncMock,
                return_value={"status": "ok"},
            ),
        ):
            response = await client.get("/health/ready")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ready"
        assert body["mongodb"]["status"] == "ok"
        assert body["weaviate"]["status"] == "ok"

    async def test_ready_503_when_mongodb_down(self, client):
        with (
            patch(
                "src.api.main.get_mongodb_status",
                new_callable=AsyncMock,
                return_value={"status": "error", "detail": "connection refused"},
            ),
            patch(
                "src.api.main.get_weaviate_status",
                new_callable=AsyncMock,
                return_value={"status": "ok"},
            ),
        ):
            response = await client.get("/health/ready")

        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "not ready"
        assert body["mongodb"]["status"] == "error"

    async def test_ready_503_when_weaviate_down(self, client):
        with (
            patch(
                "src.api.main.get_mongodb_status",
                new_callable=AsyncMock,
                return_value={"status": "ok"},
            ),
            patch(
                "src.api.main.get_weaviate_status",
                new_callable=AsyncMock,
                return_value={"status": "error", "detail": "not ready"},
            ),
        ):
            response = await client.get("/health/ready")

        assert response.status_code == 503
        assert response.json()["status"] == "not ready"

    async def test_ready_503_when_both_down(self, client):
        with (
            patch(
                "src.api.main.get_mongodb_status",
                new_callable=AsyncMock,
                return_value={"status": "error", "detail": "timeout"},
            ),
            patch(
                "src.api.main.get_weaviate_status",
                new_callable=AsyncMock,
                return_value={"status": "error", "detail": "timeout"},
            ),
        ):
            response = await client.get("/health/ready")

        assert response.status_code == 503

    async def test_ready_includes_detail_on_error(self, client):
        with (
            patch(
                "src.api.main.get_mongodb_status",
                new_callable=AsyncMock,
                return_value={"status": "error", "detail": "connection refused"},
            ),
            patch(
                "src.api.main.get_weaviate_status",
                new_callable=AsyncMock,
                return_value={"status": "ok"},
            ),
        ):
            response = await client.get("/health/ready")

        assert "connection refused" in response.json()["mongodb"]["detail"]


class TestGetMongodbStatus:
    async def test_returns_error_when_not_initialized(self):
        import src.db.mongodb as mongodb_module
        from src.db.mongodb import get_mongodb_status

        original = mongodb_module._client
        mongodb_module._client = None
        try:
            result = await get_mongodb_status()
            assert result["status"] == "error"
            assert "not initialized" in result["detail"]
        finally:
            mongodb_module._client = original

    async def test_returns_ok_when_ping_succeeds(self):
        from unittest.mock import MagicMock

        import src.db.mongodb as mongodb_module
        from src.db.mongodb import get_mongodb_status

        mock_client = MagicMock()
        mock_client.admin.command = AsyncMock(return_value={"ok": 1})

        original = mongodb_module._client
        mongodb_module._client = mock_client
        try:
            result = await get_mongodb_status()
            assert result["status"] == "ok"
        finally:
            mongodb_module._client = original

    async def test_returns_error_when_ping_fails(self):
        from unittest.mock import MagicMock

        import src.db.mongodb as mongodb_module
        from src.db.mongodb import get_mongodb_status

        mock_client = MagicMock()
        mock_client.admin.command = AsyncMock(
            side_effect=Exception("connection refused")
        )

        original = mongodb_module._client
        mongodb_module._client = mock_client
        try:
            result = await get_mongodb_status()
            assert result["status"] == "error"
            assert "connection refused" in result["detail"]
        finally:
            mongodb_module._client = original


class TestGetWeaviateStatus:
    async def test_returns_error_when_not_initialized(self):
        import src.db.weaviate_client as weaviate_module
        from src.db.weaviate_client import get_weaviate_status

        original = weaviate_module._client
        weaviate_module._client = None
        try:
            result = await get_weaviate_status()
            assert result["status"] == "error"
            assert "not initialized" in result["detail"]
        finally:
            weaviate_module._client = original

    async def test_returns_ok_when_ready(self):
        from unittest.mock import MagicMock

        import src.db.weaviate_client as weaviate_module
        from src.db.weaviate_client import get_weaviate_status

        mock_client = MagicMock()
        mock_client.is_ready = AsyncMock(return_value=True)

        original = weaviate_module._client
        weaviate_module._client = mock_client
        try:
            result = await get_weaviate_status()
            assert result["status"] == "ok"
        finally:
            weaviate_module._client = original

    async def test_returns_error_when_not_ready(self):
        from unittest.mock import MagicMock

        import src.db.weaviate_client as weaviate_module
        from src.db.weaviate_client import get_weaviate_status

        mock_client = MagicMock()
        mock_client.is_ready = AsyncMock(return_value=False)

        original = weaviate_module._client
        weaviate_module._client = mock_client
        try:
            result = await get_weaviate_status()
            assert result["status"] == "error"
            assert "not ready" in result["detail"]
        finally:
            weaviate_module._client = original
