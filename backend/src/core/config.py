"""
Application configuration using Pydantic Settings.

Loads environment variables from a .env file at the project root, validates
them at startup, and exposes a typed `settings` singleton for the entire app.

Design decisions
----------------
Why Pydantic Settings (not python-decouple or dynaconf):
    - Type safety with IDE autocomplete on every config value.
    - Validation at startup — if MONGODB_URL is missing, the app fails
      immediately with a clear error instead of crashing later at runtime.
    - Shares the Pydantic ecosystem with FastAPI schemas and Beanie documents,
      so there is one validation library to learn, not three.
    - Works with .env files out of the box via SettingsConfigDict.

    python-decouple: simpler but returns raw strings — no type coercion or
    validation. Good for small scripts, not for a 12-collection production app.

    dynaconf: feature-rich (multi-env, YAML, TOML) but heavier than we need.
    We use one .env file per environment; Pydantic Settings handles that.

Why a composed root Settings class (not one flat class):
    Grouping related settings into sub-models (MongoDBSettings, AuthSettings,
    etc.) keeps each group small and testable. The root Settings class composes
    them. This is the approach recommended by the Pydantic Settings docs for
    medium-to-large applications.

    Alternative: one flat Settings class with 20+ fields. Works for small
    projects but gets hard to navigate as the config grows.

Why @lru_cache for the get_settings() function:
    Creates a singleton — the .env file is read once, not on every import.
    FastAPI's Depends(get_settings) integrates cleanly with this pattern.
    The cache can be cleared in tests to inject different config values.

Usage
-----
    from src.core.config import get_settings

    settings = get_settings()
    print(settings.mongodb.url)
    print(settings.auth.jwt_secret_key)

In FastAPI dependency injection:
    from fastapi import Depends
    from src.core.config import Settings, get_settings

    @app.get("/health")
    async def health(settings: Settings = Depends(get_settings)):
        return {"app": settings.app_name}
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# ---------------------------------------------------------------------------
# Resolve .env file path relative to project root.
# This file lives at src/core/config.py, so project root is two levels up.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class AppSettings(BaseSettings):
    """General application settings."""

    model_config = SettingsConfigDict(env_prefix="APP_")

    name: str = "reqruit"
    env: str = "development"
    debug: bool = True
    version: str = "0.1.0"


class MongoDBSettings(BaseSettings):
    """
    MongoDB connection settings.

    Beanie 2.0 uses PyMongo's native async API (not Motor) under the hood.
    The URL follows standard MongoDB connection string format:
        mongodb://[user:password@]host[:port][/database][?options]
    """

    model_config = SettingsConfigDict(env_prefix="MONGODB_")

    url: str = "mongodb://localhost:27017"
    database: str = "job_hunt"


class WeaviateSettings(BaseSettings):
    """
    Weaviate vector database settings.

    Local development uses anonymous access (no API key).
    Production with Weaviate Cloud Services (WCS) requires an API key.
    """

    model_config = SettingsConfigDict(env_prefix="WEAVIATE_")

    url: str = "http://localhost:8080"
    api_key: str = ""


class AuthSettings(BaseSettings):
    """
    JWT authentication settings.

    We use PyJWT (not python-jose, which is unmaintained since 2021).
    HS256 is the default algorithm — symmetric, fast, sufficient for a
    single-service app. RS256 (asymmetric) would be needed if multiple
    services verify tokens independently.

    Access token lifetime: 15 minutes (short — limits damage from theft).
    Refresh token lifetime: 7 days (convenience — users re-login weekly).
    """

    model_config = SettingsConfigDict(env_prefix="")

    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7


class AnthropicSettings(BaseSettings):
    """Anthropic Claude API configuration (primary LLM provider)."""

    model_config = SettingsConfigDict(env_prefix="ANTHROPIC_")

    api_key: str = ""


class OpenAISettings(BaseSettings):
    """
    OpenAI API configuration (secondary LLM provider).

    Also used for the free OpenAI Moderation API (input guardrails).
    """

    model_config = SettingsConfigDict(env_prefix="OPENAI_")

    api_key: str = ""


class GroqSettings(BaseSettings):
    """
    Groq API configuration (free LLM fallback).

    Free tier: 500K tokens/day, 30 requests/minute.
    Provides Llama 3.3 70B and Llama 3.1 8B for non-critical tasks.
    No embedding models available — LLM inference only.
    """

    model_config = SettingsConfigDict(env_prefix="GROQ_")

    api_key: str = ""


class EmbeddingSettings(BaseSettings):
    """
    Embedding model settings for BGE-small-en-v1.5.

    App-side embeddings (not Weaviate vectorizer modules) give us full control
    over the model — no API costs, no vendor lock-in, works offline. The model
    is ~130MB and loads in 2-3 seconds.

    BGE-small-en-v1.5 produces 384-dimensional vectors trained with cosine
    similarity, matching our Weaviate HNSW index configuration.
    """

    model_config = SettingsConfigDict(env_prefix="EMBEDDING_")

    model_name: str = "BAAI/bge-small-en-v1.5"
    dimensions: int = 384
    cache_dir: str = ""  # Empty = default HuggingFace cache


class LangSmithSettings(BaseSettings):
    """
    LangSmith observability settings.

    Set tracing_v2=false to disable tracing (e.g., in production or CI).
    Free tier: 5K traces/month — sufficient for development.
    """

    model_config = SettingsConfigDict(env_prefix="LANGCHAIN_")

    tracing_v2: bool = Field(default=False, alias="LANGCHAIN_TRACING_V2")
    api_key: str = Field(default="", alias="LANGCHAIN_API_KEY")
    project: str = Field(
        default="reqruit", alias="LANGCHAIN_PROJECT"
    )


class RateLimitSettings(BaseSettings):
    """Per-user rate limiting for LLM endpoints."""

    model_config = SettingsConfigDict(env_prefix="RATE_LIMIT_")

    max_llm_requests_per_hour: int = 10
    rate_limit_window_seconds: int = 3600


class LocaleSettings(BaseSettings):
    """Locale service configuration."""

    model_config = SettingsConfigDict(env_prefix="LOCALE_")

    market_config_cache_ttl_seconds: int = 3600  # 1 hour
    currency_refresh_interval_hours: int = 4


class ExternalAPISettings(BaseSettings):
    """External API keys and configuration for third-party services."""

    model_config = SettingsConfigDict(env_prefix="EXTERNAL_")

    frankfurter_base_url: str = "https://api.frankfurter.app"
    jsearch_api_key: str = ""
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""


class RedisSettings(BaseSettings):
    """
    Redis connection settings for the async client.

    Used by the task queue broker and result backend. Default URL uses
    database 0; Celery broker and result backend use databases 1 and 2
    to avoid key collisions.
    """

    model_config = SettingsConfigDict(env_prefix="REDIS_")

    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 20
    redis_socket_timeout: float = 5.0


class TierSettings(BaseSettings):
    """Per-tier usage limits for LLM cost management."""

    model_config = SettingsConfigDict(env_prefix="TIER_")

    free_weekly_cost_usd: float = 1.50
    free_weekly_tokens: int = 500_000
    pro_weekly_cost_usd: float = 15.0
    pro_weekly_tokens: int = 5_000_000
    admin_unlimited: bool = True


class OAuthSettings(BaseSettings):
    """OAuth integration settings for email/calendar providers."""

    model_config = SettingsConfigDict(env_prefix="")

    encryption_key: str = Field(
        default="0" * 64,
        alias="OAUTH_ENCRYPTION_KEY",
    )
    gmail_client_id: str = Field(default="", alias="GMAIL_CLIENT_ID")
    gmail_client_secret: str = Field(default="", alias="GMAIL_CLIENT_SECRET")
    gmail_redirect_uri: str = Field(default="", alias="GMAIL_REDIRECT_URI")
    google_calendar_client_id: str = Field(
        default="", alias="GOOGLE_CALENDAR_CLIENT_ID"
    )
    google_calendar_client_secret: str = Field(
        default="", alias="GOOGLE_CALENDAR_CLIENT_SECRET"
    )
    google_calendar_redirect_uri: str = Field(
        default="", alias="GOOGLE_CALENDAR_REDIRECT_URI"
    )


class CelerySettings(BaseSettings):
    """
    Celery task queue configuration.

    acks_late + reject_on_worker_lost ensures zero task loss: tasks are
    only acknowledged after completion, and if a worker dies mid-task the
    message is returned to the queue for another worker to pick up.
    """

    model_config = SettingsConfigDict(env_prefix="CELERY_")

    broker_url: str = "redis://localhost:6379/1"
    result_backend: str = "redis://localhost:6379/2"
    task_default_queue: str = "batch"
    task_acks_late: bool = True
    worker_prefetch_multiplier: int = 1
    task_reject_on_worker_lost: bool = True
    task_track_started: bool = True
    beat_schedule_filename: str = "/tmp/celerybeat-schedule"


class Settings(BaseSettings):
    """
    Root configuration — composes all sub-settings into one object.

    Each sub-setting reads its own environment variables (via env_prefix).
    The root class loads the .env file so all sub-settings can find their
    values.

    Access pattern:
        settings = get_settings()
        settings.app.name          # -> APP_NAME
        settings.mongodb.url       # -> MONGODB_URL
        settings.auth.jwt_secret_key  # -> JWT_SECRET_KEY
    """

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Sub-settings are composed, not inherited. Each manages its own
    # env_prefix and validation. This keeps each group independent and
    # easy to test in isolation.
    app: AppSettings = Field(default_factory=AppSettings)
    mongodb: MongoDBSettings = Field(default_factory=MongoDBSettings)
    weaviate: WeaviateSettings = Field(default_factory=WeaviateSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    anthropic: AnthropicSettings = Field(default_factory=AnthropicSettings)
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    groq: GroqSettings = Field(default_factory=GroqSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    langsmith: LangSmithSettings = Field(default_factory=LangSmithSettings)
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)
    locale: LocaleSettings = Field(default_factory=LocaleSettings)
    external_api: ExternalAPISettings = Field(default_factory=ExternalAPISettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    celery: CelerySettings = Field(default_factory=CelerySettings)
    tier: TierSettings = Field(default_factory=TierSettings)
    oauth: OAuthSettings = Field(default_factory=OAuthSettings)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the application settings singleton.

    Uses @lru_cache so the .env file is read exactly once. Subsequent calls
    return the cached instance. In tests, call get_settings.cache_clear()
    before injecting a different Settings object.
    """
    return Settings()
