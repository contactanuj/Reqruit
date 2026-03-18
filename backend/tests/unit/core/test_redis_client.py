"""Tests for Redis async singleton client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.config import RedisSettings


class TestInitRedis:
    async def test_creates_connection_and_pings(self):
        """init_redis() creates a Redis connection and verifies with ping."""
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(return_value=True)

        settings = RedisSettings()

        with patch("src.core.redis_client.aioredis") as mock_aioredis:
            mock_aioredis.from_url.return_value = mock_client

            # Reset module state
            import src.core.redis_client as mod
            mod._redis_client = None

            result = await mod.init_redis(settings)

            mock_aioredis.from_url.assert_called_once_with(
                settings.redis_url,
                max_connections=settings.redis_max_connections,
                socket_timeout=settings.redis_socket_timeout,
                decode_responses=True,
            )
            mock_client.ping.assert_awaited_once()
            assert result is mock_client
            assert mod._redis_client is mock_client

            # Cleanup
            mod._redis_client = None


class TestGetRedis:
    async def test_raises_before_init(self):
        """get_redis() raises RuntimeError if called before init_redis()."""
        import src.core.redis_client as mod
        mod._redis_client = None

        with pytest.raises(RuntimeError, match="Redis not initialized"):
            mod.get_redis()

    async def test_returns_singleton_after_init(self):
        """get_redis() returns the same client set by init_redis()."""
        import src.core.redis_client as mod
        mock_client = MagicMock()
        mod._redis_client = mock_client

        result = mod.get_redis()

        assert result is mock_client

        # Cleanup
        mod._redis_client = None

    async def test_returns_same_instance_on_repeated_calls(self):
        """get_redis() returns the same singleton on every call."""
        import src.core.redis_client as mod
        mock_client = MagicMock()
        mod._redis_client = mock_client

        result1 = mod.get_redis()
        result2 = mod.get_redis()

        assert result1 is result2 is mock_client

        # Cleanup
        mod._redis_client = None


class TestCloseRedis:
    async def test_closes_client_and_resets_singleton(self):
        """close_redis() calls close() on client and resets to None."""
        import src.core.redis_client as mod
        mock_client = AsyncMock()
        mod._redis_client = mock_client

        await mod.close_redis()

        mock_client.close.assert_awaited_once()
        assert mod._redis_client is None

    async def test_idempotent_when_already_none(self):
        """close_redis() is safe to call when client is already None."""
        import src.core.redis_client as mod
        mod._redis_client = None

        await mod.close_redis()  # Should not raise

        assert mod._redis_client is None
