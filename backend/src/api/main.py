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
from bson.errors import InvalidId
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.middleware.locale import LocaleContextMiddleware
from src.api.middleware.logging import RequestLoggingMiddleware
from src.api.routes.activity import router as activity_router
from src.api.routes.admin_discovery import router as admin_discovery_router
from src.api.routes.admin_locale import router as admin_locale_router
from src.api.routes.admin_tasks import router as admin_tasks_router
from src.api.routes.admin_trust import router as admin_trust_router
from src.api.routes.admin_usage import router as admin_usage_router
from src.api.routes.application_assembly import router as application_assembly_router
from src.api.routes.apply import router as apply_router
from src.api.routes.ats_export import router as ats_export_router
from src.api.routes.auth import router as auth_router
from src.api.routes.career import router as career_router
from src.api.routes.compensation import router as compensation_router
from src.api.routes.discovery import router as discovery_router
from src.api.routes.integrations import router as integrations_router
from src.api.routes.interview_coach import router as interview_coach_router
from src.api.routes.interviews import router as interviews_router
from src.api.routes.jobs import router as jobs_router
from src.api.routes.locale import router as locale_router
from src.api.routes.locale_tools import router as locale_tools_router
from src.api.routes.market import router as market_router
from src.api.routes.negotiation import router as negotiation_router
from src.api.routes.notifications import router as notifications_router
from src.api.routes.nudges import router as nudges_router
from src.api.routes.offers import router as offers_router
from src.api.routes.outcome import router as outcome_router
from src.api.routes.outreach import router as outreach_router
from src.api.routes.profile import router as profile_router
from src.api.routes.pwa import router as pwa_router
from src.api.routes.skills import router as skills_router
from src.api.routes.tasks import router as tasks_router
from src.api.routes.track import router as track_router
from src.api.routes.trust import router as trust_router
from src.api.routes.usage import router as usage_router
from src.api.routes.wellness import router as wellness_router
from src.core.config import get_settings
from src.core.exceptions import AppError, RateLimitError
from src.core.logging import configure_logging
from src.core.redis_client import close_redis, init_redis
from src.db.mongodb import close_mongodb, connect_mongodb, get_mongodb_status
from src.db.weaviate_client import close_weaviate, connect_weaviate, get_weaviate_status
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
    configure_logging(is_development=settings.app.debug)

    # -- Secret validation (fail-fast in production) --
    if not settings.app.debug:
        if settings.auth.jwt_secret_key == "change-me-in-production":
            raise RuntimeError(
                "JWT_SECRET_KEY must be set to a strong secret in production"
            )
        if settings.oauth.encryption_key == "0" * 64:
            raise RuntimeError(
                "OAUTH_ENCRYPTION_KEY must be set to a strong key in production"
            )

    logger.info(
        "application_startup",
        app_name=settings.app.name,
        environment=settings.app.env,
    )

    # -- Startup --
    await connect_mongodb(settings)
    await init_redis(settings.redis)
    await connect_weaviate(settings)
    init_embeddings(settings)
    init_model_manager(settings)
    init_checkpointer(settings)

    # Seed baseline market configs (IN, US) — idempotent
    from src.db.seeds import seed_market_configs
    await seed_market_configs()

    from src.workflows.checkpointer import get_checkpointer
    from src.workflows.graphs.application_assembly import (
        init_application_assembly_graph,
    )
    from src.workflows.graphs.cover_letter import init_cover_letter_graph
    from src.workflows.graphs.interview_coach import init_interview_coach_graph
    from src.workflows.graphs.negotiation import init_negotiation_graph
    from src.workflows.graphs.skills_analysis import init_skills_analysis_graph
    checkpointer = get_checkpointer()
    init_cover_letter_graph(checkpointer)
    init_skills_analysis_graph(checkpointer)
    init_application_assembly_graph(checkpointer)
    init_interview_coach_graph(checkpointer)
    init_negotiation_graph(checkpointer)

    yield

    # -- Shutdown (reverse order) --
    from src.workflows.graphs.application_assembly import (
        close_application_assembly_graph,
    )
    close_application_assembly_graph()
    close_checkpointer()
    close_model_manager()
    close_embeddings()
    await close_weaviate()
    await close_redis()
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
    headers = {}
    if isinstance(exc, RateLimitError) and exc.retry_after:
        headers["Retry-After"] = str(exc.retry_after)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "detail": exc.detail,
        },
        headers=headers or None,
    )


async def invalid_id_exception_handler(
    _request: Request, exc: InvalidId
) -> JSONResponse:
    """Return 422 when a route receives a malformed BSON ObjectId."""
    return JSONResponse(
        status_code=422,
        content={
            "error_code": "INVALID_ID",
            "detail": "Invalid document ID format",
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
    application.add_exception_handler(InvalidId, invalid_id_exception_handler)

    # -- CORS middleware --
    # Permissive in development (allow all origins). In production, restrict
    # to the actual frontend domain.
    #
    # Alternative: use a reverse proxy (nginx, Caddy) for CORS. That is
    # better for production but adds infrastructure complexity during dev.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.app.debug else getattr(settings.app, "cors_origins", ["*"]),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -- Request logging middleware --
    # Must be added after CORS so CORS headers are set before logging runs.
    application.add_middleware(RequestLoggingMiddleware)

    # -- Locale context middleware --
    # Injects user locale profile into request.state for downstream handlers.
    application.add_middleware(LocaleContextMiddleware)

    # -- Routes --
    _register_routes(application)

    return application


def _register_routes(application: FastAPI) -> None:
    """
    Register all API routes.
    """
    application.include_router(auth_router)
    application.include_router(profile_router)
    application.include_router(jobs_router)
    application.include_router(apply_router)
    application.include_router(track_router)
    application.include_router(interviews_router)
    application.include_router(outreach_router)
    application.include_router(locale_router)
    application.include_router(locale_tools_router)
    application.include_router(admin_locale_router)
    application.include_router(skills_router)
    # Phase 2: Application Intelligence
    application.include_router(outcome_router)
    application.include_router(application_assembly_router)
    application.include_router(interview_coach_router)
    # Phase 3: Negotiation War Room
    application.include_router(offers_router)
    application.include_router(negotiation_router)
    application.include_router(compensation_router)
    # Phase 4: Trust & Safety
    application.include_router(trust_router)
    application.include_router(admin_trust_router)
    # Phase 4: Gamification
    application.include_router(activity_router)
    application.include_router(wellness_router)
    # Phase 5: Career Operating System
    application.include_router(career_router)
    # Phase 5: Market Intelligence
    application.include_router(market_router)
    # Phase 6: Platform Maturity
    application.include_router(tasks_router)
    application.include_router(admin_tasks_router)
    application.include_router(usage_router)
    application.include_router(admin_usage_router)
    # Phase 6: Integrations
    application.include_router(integrations_router)
    # Phase 6: Nudges
    application.include_router(nudges_router)
    # Phase 6: Discovery
    application.include_router(discovery_router)
    application.include_router(admin_discovery_router)
    # Phase 6: ATS Export
    application.include_router(ats_export_router)
    # Phase 6: PWA
    application.include_router(pwa_router)
    # Phase 6: Notifications
    application.include_router(notifications_router)

    @application.get("/health", tags=["system"], summary="Liveness check")
    async def health_check() -> dict:
        """Liveness check — returns 200 if the process is running."""
        settings = get_settings()
        return {
            "status": "healthy",
            "app": settings.app.name,
            "version": settings.app.version,
            "environment": settings.app.env,
        }

    @application.get("/health/ready", tags=["system"], summary="Readiness check")
    async def readiness_check() -> JSONResponse:
        """Readiness check — verifies MongoDB and Weaviate are reachable."""
        mongo_status = await get_mongodb_status()
        weaviate_status = await get_weaviate_status()
        all_ok = mongo_status["status"] == "ok" and weaviate_status["status"] == "ok"
        return JSONResponse(
            status_code=200 if all_ok else 503,
            content={
                "status": "ready" if all_ok else "not ready",
                "mongodb": mongo_status,
                "weaviate": weaviate_status,
            },
        )


# ---------------------------------------------------------------------------
# Module-level app instance for uvicorn
# ---------------------------------------------------------------------------
# uvicorn discovers this via: uvicorn src.api.main:app
# The factory pattern means tests can create separate instances.
app = create_app()
