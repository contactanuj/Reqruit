"""
MongoDB connection management using Beanie 2.0 and PyMongo's async client.

Design decisions
----------------
Why Beanie 2.0 (not Motor or raw PyMongo):
    Beanie is an async ODM (Object-Document Mapper) that treats MongoDB
    documents as Pydantic models. This gives us:
    - One class definition for DB schema + API schema + validation
    - Async CRUD operations that align with our Full Async architecture
    - Automatic index creation from document model definitions
    - Event hooks for cross-cutting concerns (timestamps, auditing)

    Beanie 2.0 uses PyMongo's native AsyncMongoClient (introduced in
    PyMongo 4.8+). Earlier versions used Motor as the async driver.
    The switch to native PyMongo eliminates the Motor dependency and
    aligns with PyMongo's official async support.

    Alternative: Motor directly. Provides async MongoDB access but without
    the ODM layer — every query requires manual dict-to-model conversion.

    Alternative: MongoEngine. Mature ODM but synchronous only, which
    violates our Full Async architecture decision.

Why module-level _client (not a connection pool class):
    The MongoDB client manages its own internal connection pool. We only
    need one client instance per process. A module-level variable with
    connect/close functions is the simplest correct pattern.

    The connect/close lifecycle is managed by FastAPI's lifespan context
    manager in src/api/main.py.

Usage
-----
In the FastAPI lifespan (src/api/main.py):
    from src.db.mongodb import connect_mongodb, close_mongodb

    async def lifespan(app):
        settings = get_settings()
        await connect_mongodb(settings)
        yield
        close_mongodb()
"""

import structlog
from beanie import init_beanie
from pymongo import AsyncMongoClient

from src.core.config import Settings

logger = structlog.get_logger()

# Module-level client reference. Set by connect_mongodb(), cleared by
# close_mongodb(). The client manages its own connection pool internally.
_client: AsyncMongoClient | None = None


async def connect_mongodb(settings: Settings) -> None:
    """
    Initialize the MongoDB connection and register all Beanie documents.

    Creates an AsyncMongoClient and calls init_beanie with all 12 document
    models. After this call, document classes (User, Job, etc.) can perform
    CRUD operations directly.

    Args:
        settings: Application settings containing the MongoDB URL and
            database name.

    Raises:
        ConnectionError: If MongoDB is unreachable (connection is verified
            by init_beanie when it creates indexes).
    """
    global _client

    logger.info(
        "mongodb_connecting",
        url=settings.mongodb.url,
        database=settings.mongodb.database,
    )

    _client = AsyncMongoClient(settings.mongodb.url)

    # Import ALL_DOCUMENT_MODELS here (not at module level) to avoid
    # circular imports. The documents package imports from base_document,
    # which lives in the same db package.
    from src.db.documents import ALL_DOCUMENT_MODELS

    await init_beanie(
        database=_client[settings.mongodb.database],
        document_models=ALL_DOCUMENT_MODELS,
    )

    logger.info(
        "mongodb_connected",
        database=settings.mongodb.database,
        collections=len(ALL_DOCUMENT_MODELS),
    )


def close_mongodb() -> None:
    """
    Close the MongoDB connection.

    PyMongo's AsyncMongoClient.close() is synchronous — it signals the
    client to stop accepting new operations and close connections. Pending
    operations may still complete.

    Safe to call multiple times (idempotent).
    """
    global _client

    if _client is not None:
        _client.close()
        _client = None
        logger.info("mongodb_disconnected")


async def get_mongodb_status() -> dict:
    """
    Ping MongoDB and return a status dict for the readiness probe.

    Returns:
        {"status": "ok"} if reachable, {"status": "error", "detail": "..."} if not.
    """
    if _client is None:
        return {"status": "error", "detail": "not initialized"}
    try:
        await _client.admin.command("ping")
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


def get_mongodb_client() -> AsyncMongoClient:
    """
    Return the active MongoDB client.

    For cases where direct client access is needed (e.g., MongoDBSaver for
    LangGraph checkpoints, raw aggregation pipelines).

    Raises:
        RuntimeError: If called before connect_mongodb().
    """
    if _client is None:
        msg = "MongoDB client not initialized. Call connect_mongodb() first."
        raise RuntimeError(msg)
    return _client
