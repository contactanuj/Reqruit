"""
MongoDB checkpointer for LangGraph workflow persistence.

MongoDBSaver persists workflow checkpoints to MongoDB so users can pause and
resume multi-step job hunting workflows across server restarts. Each checkpoint
captures the full graph state (messages, analysis results, draft documents)
at a specific node, enabling human-in-the-loop review and revision cycles.

Design decisions
----------------
Why a separate sync MongoClient (not the Beanie async client):
    MongoDBSaver.__init__ requires pymongo.synchronous.mongo_client.MongoClient.
    Our Beanie setup uses pymongo.AsyncMongoClient (Beanie 2.0's native async
    driver). These are distinct classes -- MongoDBSaver internally uses
    run_in_executor for its async methods (aget_tuple, aput), wrapping
    synchronous PyMongo calls. Passing an AsyncMongoClient would fail.

    The sync client creates its own connection pool (default 100 connections).
    This is lightweight -- MongoDB handles thousands of connections efficiently,
    and checkpoint reads/writes are infrequent compared to application queries.

Why module-level lifecycle (not a class or context manager):
    Matches the established pattern in mongodb.py, weaviate_client.py, and
    manager.py:
    - _checkpointer variable holds the instance
    - init_checkpointer() creates it
    - close_checkpointer() cleans up
    - get_checkpointer() returns it or raises RuntimeError

    MongoDBSaver.from_conn_string() is a context manager that creates its own
    client. We avoid it because we want explicit lifecycle control aligned with
    FastAPI's lifespan, and we want to reuse the same connection string from
    Settings without creating/destroying clients per workflow invocation.

Usage
-----
In the FastAPI lifespan (src/api/main.py):
    from src.workflows.checkpointer import init_checkpointer, close_checkpointer

    async def lifespan(app):
        ...
        init_checkpointer(settings)
        yield
        close_checkpointer()
        ...

In a graph builder:
    from src.workflows.checkpointer import get_checkpointer

    checkpointer = get_checkpointer()
    graph = builder.compile(checkpointer=checkpointer)
"""

import structlog
from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient

from src.core.config import Settings

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Module-level lifecycle (matches mongodb.py / weaviate_client.py / manager.py)
# ---------------------------------------------------------------------------

_sync_client: MongoClient | None = None
_checkpointer: MongoDBSaver | None = None


def init_checkpointer(settings: Settings) -> None:
    """
    Initialize the LangGraph MongoDB checkpointer.

    Creates a synchronous MongoClient (separate from Beanie's async client)
    and wraps it in a MongoDBSaver. The checkpointer stores workflow state
    in two collections: 'checkpoints' and 'checkpoint_writes', both in the
    same database as the application data.

    Called during FastAPI lifespan startup, after init_model_manager().

    Args:
        settings: Application settings containing the MongoDB URL and
            database name.
    """
    global _sync_client, _checkpointer

    _sync_client = MongoClient(settings.mongodb.url)
    _checkpointer = MongoDBSaver(
        client=_sync_client,
        db_name=settings.mongodb.database,
    )

    logger.info(
        "checkpointer_initialized",
        db_name=settings.mongodb.database,
    )


def close_checkpointer() -> None:
    """
    Close the checkpointer and its sync MongoDB client.

    Called during FastAPI lifespan shutdown. Closes the sync client's
    connection pool. Safe to call multiple times (idempotent).
    """
    global _sync_client, _checkpointer

    if _sync_client is not None:
        _sync_client.close()
        _sync_client = None
    _checkpointer = None
    logger.info("checkpointer_closed")


def get_checkpointer() -> MongoDBSaver:
    """
    Return the active MongoDBSaver instance.

    Raises:
        RuntimeError: If called before init_checkpointer().
    """
    if _checkpointer is None:
        msg = "Checkpointer not initialized. Call init_checkpointer() first."
        raise RuntimeError(msg)
    return _checkpointer
