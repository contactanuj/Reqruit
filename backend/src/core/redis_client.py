"""
Redis async singleton client for task queue and caching.

Follows the same singleton pattern used by MongoDB in src/db/mongodb.py.
The module-level _redis_client is initialized once during FastAPI lifespan
startup and accessed everywhere via get_redis().

Usage
-----
    from src.core.redis_client import init_redis, get_redis, close_redis

    # In FastAPI lifespan startup:
    await init_redis(settings.redis)

    # Anywhere in the app:
    redis = get_redis()
    await redis.set("key", "value")

    # In FastAPI lifespan shutdown:
    await close_redis()
"""

import redis.asyncio as aioredis
import structlog

from src.core.config import RedisSettings

logger = structlog.get_logger()

_redis_client: aioredis.Redis | None = None


async def init_redis(settings: RedisSettings) -> aioredis.Redis:
    """
    Initialize the Redis async client singleton.

    Creates a connection pool from the settings URL, stores it in the
    module-level singleton, and verifies connectivity with a ping.

    Args:
        settings: RedisSettings with url, max_connections, socket_timeout.

    Returns:
        The initialized Redis client.

    Raises:
        redis.ConnectionError: If Redis is unreachable.
    """
    global _redis_client

    logger.info("redis_connecting", url=settings.redis_url)

    _redis_client = aioredis.from_url(
        settings.redis_url,
        max_connections=settings.redis_max_connections,
        socket_timeout=settings.redis_socket_timeout,
        decode_responses=True,
    )
    await _redis_client.ping()

    logger.info("redis_connected", url=settings.redis_url)
    return _redis_client


def get_redis() -> aioredis.Redis:
    """
    Return the Redis client singleton.

    Raises:
        RuntimeError: If called before init_redis().
    """
    if _redis_client is None:
        msg = "Redis not initialized. Call init_redis() first."
        raise RuntimeError(msg)
    return _redis_client


async def close_redis() -> None:
    """
    Close the Redis connection and reset the singleton.

    Safe to call multiple times (idempotent).
    """
    global _redis_client

    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
        logger.info("redis_disconnected")
