"""
FastAPI application factory.

Design decisions
----------------
Why a factory function (create_app) instead of module-level `app = FastAPI()`:
    A factory lets us create multiple app instances with different configs.
    This is critical for testing — each test can get a fresh app with a test
    database URL, disabled auth, or mock LLM providers without leaking state
    between tests.

    Module-level `app = FastAPI()` is simpler and common in tutorials, but it
    creates a singleton that is hard to reconfigure. For a project with 12+
    collections, multiple LLM providers, and async DB connections, the factory
    pattern pays for itself quickly.

    The convention: create_app() builds and returns the app. A module-level
    `app` variable calls create_app() for uvicorn to discover.

Why lifespan context manager (not @app.on_event):
    FastAPI deprecated @app.on_event("startup") and @app.on_event("shutdown")
    in favor of the lifespan context manager (added in FastAPI 0.93+, Starlette
    0.26+). The lifespan pattern:
    - Groups startup and shutdown in one function (easier to read).
    - Supports dependency injection via app.state.
    - Is the only approach that works with ASGI lifespan protocol correctly.

    @app.on_event still works but will be removed in a future FastAPI release.

Usage
-----
Development:
    uvicorn src.api.main:app --reload

Production (inside Docker):
    uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.core.config import get_settings
from src.core.exceptions import AppError
from src.db.mongodb import close_mongodb, connect_mongodb
from src.db.weaviate_client import close_weaviate, connect_weaviate
from src.llm.manager import close_model_manager, init_model_manager
from src.rag.embeddings import close_embeddings, init_embeddings
from src.workflows.checkpointer import close_checkpointer, init_checkpointer

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Lifespan: startup and shutdown logic
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan — runs once on startup, cleans up on shutdown.

    Startup order matters:
        1. MongoDB first — Beanie registers document models and creates indexes.
        2. Weaviate second — ensures vector collections exist.
        3. Embeddings third — loads BGE-small-en-v1.5 (~130MB, 2-3 seconds).
           After Weaviate because embeddings are the vectors that go into it.
        4. ModelManager fourth — detects available LLM providers from API keys.
           Runs after MongoDB because the cost tracking callback uses Beanie
           to insert LLMUsage records.
        5. Checkpointer fifth — creates a separate sync MongoClient for
           LangGraph's MongoDBSaver. Runs after MongoDB so the database exists.

    Shutdown order is reversed (close last-opened first) to avoid dangling
    references.
    """
    settings = get_settings()
    logger.info(
        "application_startup",
        app_name=settings.app.name,
        environment=settings.app.env,
    )

    # -- Startup --
    await connect_mongodb(settings)
    await connect_weaviate(settings)
    init_embeddings(settings)
    init_model_manager(settings)
    init_checkpointer(settings)

    yield

    # -- Shutdown (reverse order) --
    close_checkpointer()
    close_model_manager()
    close_embeddings()
    await close_weaviate()
    close_mongodb()
    logger.info("application_shutdown")


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------


async def app_exception_handler(
    _request: Request, exc: AppError
) -> JSONResponse:
    """
    Maps domain exceptions to structured JSON error responses.

    Every AppError carries a status_code, error_code, and detail.
    The frontend/consumer can switch on error_code for programmatic handling
    (e.g., redirect to login on AUTH_TOKEN_EXPIRED) and display detail to
    the user.

    Response format:
        {
            "error_code": "JOB_NOT_FOUND",
            "detail": "Job abc123 not found"
        }

    This pattern is used by Stripe, GitHub, and other production APIs.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "detail": exc.detail,
        },
    )


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    """
    Build and configure the FastAPI application.

    This factory is called once at import time (see module-level `app` below).
    Tests can call it directly with a different Settings object to override
    configuration.
    """
    settings = get_settings()

    application = FastAPI(
        title=settings.app.name,
        version=settings.app.version,
        debug=settings.app.debug,
        lifespan=lifespan,
        # Disable docs in production to reduce attack surface.
        # In development, Swagger UI is at /docs and ReDoc at /redoc.
        docs_url="/docs" if settings.app.debug else None,
        redoc_url="/redoc" if settings.app.debug else None,
    )

    # -- Exception handlers --
    # Register our domain exception handler. FastAPI's built-in handlers
    # for RequestValidationError and HTTPException remain active.
    application.add_exception_handler(AppError, app_exception_handler)

    # -- CORS middleware --
    # Permissive in development (allow all origins). In production, restrict
    # to the actual frontend domain.
    #
    # Alternative: use a reverse proxy (nginx, Caddy) for CORS. That is
    # better for production but adds infrastructure complexity during dev.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.app.debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -- Routes --
    _register_routes(application)

    return application


def _register_routes(application: FastAPI) -> None:
    """
    Register all API routes.

    Route modules will be added as APIRouters in later modules:
        - /auth    (Module 7: API Layer)
        - /profile (Module 4: Agent Architecture)
        - /jobs    (Module 4: Agent Architecture)
        - etc.
    """

    @application.get(
        "/health",
        tags=["system"],
        summary="Health check",
    )
    async def health_check() -> dict:
        """
        Basic health check endpoint.

        Returns HTTP 200 if the application is running. Does not verify
        database connectivity — that belongs in a separate /health/ready
        endpoint (added in Module 2 when DB connections are implemented).
        """
        settings = get_settings()
        return {
            "status": "healthy",
            "app": settings.app.name,
            "version": settings.app.version,
            "environment": settings.app.env,
        }


# ---------------------------------------------------------------------------
# Module-level app instance for uvicorn
# ---------------------------------------------------------------------------
# uvicorn discovers this via: uvicorn src.api.main:app
# The factory pattern means tests can create separate instances.
app = create_app()
