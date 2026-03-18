"""
FastAPI dependency injection.

Design decisions
----------------
Why dependency injection (not global imports):
    FastAPI's Depends() system provides request-scoped dependencies that are
    easy to override in tests. Instead of importing a global db_client, each
    endpoint declares what it needs:

        @app.get("/jobs")
        async def list_jobs(repo: JobRepository = Depends(get_job_repository)):
            ...

    In tests, you override the dependency with a mock:
        app.dependency_overrides[get_job_repository] = lambda: MockJobRepo()

    This pattern decouples endpoint logic from infrastructure and is the
    standard approach in production FastAPI applications.

Why get_current_user uses HTTPBearer + PyJWT (not python-jose):
    python-jose is unmaintained since 2021. PyJWT is actively maintained,
    simpler, and sufficient for HS256 symmetric tokens in a single-service app.

    HTTPBearer raises 401 automatically when the Authorization header is
    missing. The dependency then decodes and validates the JWT, looking up
    the User from MongoDB to ensure the account still exists and is active.

    This means every authenticated request makes one MongoDB lookup — an
    acceptable trade-off for a personal-scale application. In high-traffic
    systems, you would cache the user in Redis or use a token introspection
    endpoint.
"""

import jwt
from beanie import PydanticObjectId
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.config import get_settings
from src.core.exceptions import AuthenticationError
from src.db.documents.user import User
from src.repositories.application_repository import ApplicationRepository
from src.repositories.base import BaseRepository
from src.repositories.company_repository import CompanyRepository
from src.repositories.contact_repository import ContactRepository
from src.repositories.document_repository import DocumentRepository
from src.repositories.interview_performance_repository import (
    InterviewPerformanceRepository,
)
from src.repositories.interview_repository import InterviewRepository
from src.repositories.job_repository import JobRepository
from src.repositories.llm_usage_repository import LLMUsageRepository
from src.repositories.market_config_repository import MarketConfigRepository
from src.repositories.mock_session_repository import MockSessionRepository
from src.repositories.negotiation_session_repository import NegotiationSessionRepository
from src.repositories.offer_repository import OfferRepository
from src.repositories.outreach_repository import OutreachMessageRepository
from src.repositories.profile_repository import ProfileRepository
from src.repositories.refresh_token_repository import RefreshTokenRepository
from src.repositories.resume_repository import ResumeRepository
from src.repositories.salary_benchmark_repository import SalaryBenchmarkRepository
from src.repositories.scam_report_repository import ScamReportRepository
from src.repositories.skills_profile_repository import SkillsProfileRepository
from src.repositories.star_story_repository import STARStoryRepository
from src.repositories.success_tracker_repository import (
    ApplicationSuccessTrackerRepository,
)
from src.repositories.task_record_repository import TaskRecordRepository
from src.repositories.user_activity_repository import UserActivityRepository
from src.repositories.user_repository import UserRepository
from src.repositories.variable_pay_benchmark_repository import (
    VariablePayBenchmarkRepository,
)
from src.repositories.weaviate_base import WeaviateRepository
from src.services.currency_service import CurrencyService
from src.services.indexing_service import IndexingService
from src.services.locale_service import LocaleService
from src.services.outcome_service import OutcomeService
from src.services.success_analytics import SuccessAnalyticsService

# ---------------------------------------------------------------------------
# Security scheme
# ---------------------------------------------------------------------------

_bearer = HTTPBearer()


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),  # noqa: B008
) -> User:
    """
    Extract and validate the current user from the JWT Bearer token.

    Decodes the token using PyJWT with HS256. Raises 401 if:
    - Token is expired or invalid
    - User ID is missing from the payload
    - User does not exist in the database
    - User account is inactive (soft-deleted)
    """
    settings = get_settings()
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.auth.jwt_secret_key,
            algorithms=[settings.auth.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as err:
        raise AuthenticationError("Token has expired", error_code="AUTH_TOKEN_EXPIRED") from err
    except jwt.InvalidTokenError as err:
        raise AuthenticationError("Invalid token", error_code="AUTH_TOKEN_INVALID") from err

    if payload.get("type") != "access":
        raise AuthenticationError("Invalid token type", error_code="AUTH_TOKEN_INVALID")

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Token missing subject", error_code="AUTH_TOKEN_INVALID")

    user = await User.get(PydanticObjectId(user_id))
    if user is None:
        raise AuthenticationError("User not found", error_code="AUTH_USER_NOT_FOUND")
    if not user.is_active:
        raise AuthenticationError("Account is inactive", error_code="AUTH_ACCOUNT_INACTIVE")

    return user


async def get_current_admin_user(
    user: User = Depends(get_current_user),
) -> User:
    """Require the current user to have admin privileges."""
    if not getattr(user, "is_admin", False):
        from src.core.exceptions import AuthorizationError
        raise AuthorizationError("Admin access required")
    return user


# ---------------------------------------------------------------------------
# Repository providers
# ---------------------------------------------------------------------------


def get_user_repository() -> UserRepository:
    """Provide a UserRepository instance."""
    return UserRepository()


def get_profile_repository() -> ProfileRepository:
    """Provide a ProfileRepository instance."""
    return ProfileRepository()


def get_resume_repository() -> ResumeRepository:
    """Provide a ResumeRepository instance."""
    return ResumeRepository()


def get_job_repository() -> JobRepository:
    """Provide a JobRepository instance."""
    return JobRepository()


def get_application_repository() -> ApplicationRepository:
    """Provide an ApplicationRepository instance."""
    return ApplicationRepository()


def get_document_repository() -> DocumentRepository:
    """Provide a DocumentRepository instance."""
    return DocumentRepository()


def get_llm_usage_repository() -> LLMUsageRepository:
    """Provide an LLMUsageRepository instance."""
    return LLMUsageRepository()


def get_company_repository() -> CompanyRepository:
    """Provide a CompanyRepository instance."""
    return CompanyRepository()


def get_contact_repository() -> ContactRepository:
    """Provide a ContactRepository instance."""
    return ContactRepository()


def get_refresh_token_repository() -> RefreshTokenRepository:
    """Provide a RefreshTokenRepository instance."""
    return RefreshTokenRepository()


def get_outreach_message_repository() -> OutreachMessageRepository:
    """Provide an OutreachMessageRepository instance."""
    return OutreachMessageRepository()


def get_star_story_repository() -> STARStoryRepository:
    """Provide a STARStoryRepository instance."""
    return STARStoryRepository()


def get_interview_repository() -> InterviewRepository:
    """Provide an InterviewRepository instance."""
    return InterviewRepository()


def get_mock_session_repository() -> MockSessionRepository:
    """Provide a MockSessionRepository instance."""
    return MockSessionRepository()


def get_market_config_repository() -> MarketConfigRepository:
    """Provide a MarketConfigRepository instance."""
    return MarketConfigRepository()


def get_skills_profile_repository() -> SkillsProfileRepository:
    """Provide a SkillsProfileRepository instance."""
    return SkillsProfileRepository()


def get_locale_service():
    """Provide a LocaleService instance with its dependencies."""
    settings = get_settings()
    return LocaleService(
        market_config_repo=MarketConfigRepository(),
        currency_service=CurrencyService(
            base_url=settings.external_api.frankfurter_base_url,
        ),
        cache_ttl=settings.locale.market_config_cache_ttl_seconds,
    )


# ---------------------------------------------------------------------------
# Service factories (for background tasks where Depends() is unavailable)
# ---------------------------------------------------------------------------


def build_indexing_service():
    """
    Construct an IndexingService with fresh repository instances.

    Used inside background tasks where FastAPI's Depends() is not available.
    Repositories are cheap to construct -- they just wrap Beanie documents
    and Weaviate collection names.
    """
    from src.db.documents.document_record import DocumentRecord
    from src.db.documents.job import Job
    from src.db.documents.resume import Resume
    from src.db.documents.star_story import STARStory

    return IndexingService(
        resume_repo=BaseRepository(Resume),
        job_repo=BaseRepository(Job),
        star_story_repo=BaseRepository(STARStory),
        document_repo=BaseRepository(DocumentRecord),
        resume_chunk_weaviate=WeaviateRepository("ResumeChunk"),
        job_embedding_weaviate=WeaviateRepository("JobEmbedding"),
        cover_letter_weaviate=WeaviateRepository("CoverLetterEmbedding"),
        star_story_weaviate=WeaviateRepository("STARStoryEmbedding"),
    )


# ---------------------------------------------------------------------------
# Workflow graph provider
# ---------------------------------------------------------------------------

from langgraph.graph.state import CompiledStateGraph  # noqa: E402


def get_cover_letter_graph() -> CompiledStateGraph:
    """Provide the compiled cover letter workflow graph."""
    from src.workflows.graphs.cover_letter import get_cover_letter_graph as _get_graph

    return _get_graph()


def get_skills_analysis_graph() -> CompiledStateGraph:
    """Provide the compiled skills analysis workflow graph."""
    from src.workflows.graphs.skills_analysis import (
        get_skills_analysis_graph as _get_graph,
    )

    return _get_graph()


# --- Phase 2: Application Intelligence ---


def get_interview_performance_repository() -> InterviewPerformanceRepository:
    """Provide an InterviewPerformanceRepository instance."""
    return InterviewPerformanceRepository()


def get_application_assembly_graph() -> CompiledStateGraph:
    """Provide the compiled application assembly workflow graph."""
    from src.workflows.graphs.application_assembly import (
        get_application_assembly_graph as _get_graph,
    )

    return _get_graph()


def get_interview_coach_graph() -> CompiledStateGraph:
    """Provide the compiled interview coach workflow graph."""
    from src.workflows.graphs.interview_coach import (
        get_interview_coach_graph as _get_graph,
    )

    return _get_graph()


def get_success_analytics_service():
    """Provide a SuccessAnalyticsService with a fresh tracker repository."""
    return SuccessAnalyticsService(ApplicationSuccessTrackerRepository())


def get_success_tracker_repository():
    """Provide an ApplicationSuccessTrackerRepository instance."""
    return ApplicationSuccessTrackerRepository()


def get_offer_repository() -> OfferRepository:
    """Provide an OfferRepository instance."""
    return OfferRepository()


def get_salary_benchmark_repository() -> SalaryBenchmarkRepository:
    """Provide a SalaryBenchmarkRepository instance."""
    return SalaryBenchmarkRepository()


def get_negotiation_session_repository() -> NegotiationSessionRepository:
    """Provide a NegotiationSessionRepository instance."""
    return NegotiationSessionRepository()


def get_outcome_service():
    """Provide an OutcomeService with its dependencies."""
    return OutcomeService(
        tracker_repo=ApplicationSuccessTrackerRepository(),
        app_repo=ApplicationRepository(),
    )

def get_variable_pay_benchmark_repository() -> VariablePayBenchmarkRepository:
    """Provide a VariablePayBenchmarkRepository instance."""
    return VariablePayBenchmarkRepository()

def get_scam_report_repository() -> ScamReportRepository:
    """Provide a ScamReportRepository instance."""
    return ScamReportRepository()


def get_user_activity_repository() -> UserActivityRepository:
    """Provide a UserActivityRepository instance."""
    return UserActivityRepository()


def get_task_service():
    """Provide a TaskService with its dependencies."""
    from src.services.task_service import TaskService
    from src.tasks.celery_app import celery_app

    return TaskService(repo=TaskRecordRepository(), celery=celery_app)


def get_usage_service():
    """Provide a UsageService with its dependencies."""
    from src.repositories.usage_ledger_repository import UsageLedgerRepository
    from src.services.usage_service import UsageService

    settings = get_settings()
    return UsageService(repo=UsageLedgerRepository(), tier_settings=settings.tier)


def get_integration_service():
    """Provide an IntegrationService with its dependencies."""
    from src.core.token_encryptor import TokenEncryptor
    from src.integrations.gmail_client import GmailClient
    from src.integrations.google_calendar_client import GoogleCalendarClient
    from src.repositories.calendar_signal_repository import CalendarSignalRepository
    from src.repositories.email_signal_repository import EmailSignalRepository
    from src.repositories.integration_connection_repository import (
        IntegrationConnectionRepository,
    )
    from src.services.integration_service import IntegrationService

    settings = get_settings()
    key_bytes = bytes.fromhex(settings.oauth.encryption_key)
    encryptor = TokenEncryptor(key_bytes)
    gmail_client = GmailClient(
        client_id=settings.oauth.gmail_client_id,
        client_secret=settings.oauth.gmail_client_secret,
        redirect_uri=settings.oauth.gmail_redirect_uri,
    )
    calendar_client = GoogleCalendarClient(
        client_id=settings.oauth.google_calendar_client_id,
        client_secret=settings.oauth.google_calendar_client_secret,
        redirect_uri=settings.oauth.google_calendar_redirect_uri,
    )
    repo = IntegrationConnectionRepository(encryptor)
    return IntegrationService(
        repo=repo,
        gmail_client=gmail_client,
        encryption_key=key_bytes,
        signal_repo=EmailSignalRepository(),
        calendar_client=calendar_client,
        calendar_signal_repo=CalendarSignalRepository(),
    )


def get_job_shortlist_repository():
    """Provide a JobShortlistRepository instance."""
    from src.repositories.job_shortlist_repository import JobShortlistRepository

    return JobShortlistRepository()


def get_discovery_service():
    """Provide a JobDiscoveryService with its dependencies."""
    from src.repositories.job_shortlist_repository import JobShortlistRepository
    from src.services.job_discovery_service import JobDiscoveryService

    return JobDiscoveryService(
        profile_repo=ProfileRepository(),
        shortlist_repo=JobShortlistRepository(),
    )


def get_nudge_repository():
    """Provide a NudgeRepository instance."""
    from src.repositories.nudge_repository import NudgeRepository

    return NudgeRepository()


def get_nudge_engine():
    """Provide a NudgeEngine instance with its dependencies."""
    from src.core.token_encryptor import get_token_encryptor
    from src.repositories.integration_connection_repository import (
        IntegrationConnectionRepository,
    )
    from src.repositories.nudge_repository import NudgeRepository
    from src.services.nudge_engine import NudgeEngine

    encryptor = get_token_encryptor()
    return NudgeEngine(
        nudge_repo=NudgeRepository(),
        integration_repo=IntegrationConnectionRepository(encryptor),
    )


def get_jd_cache_repository():
    """Provide a JDCacheRepository instance."""
    from src.repositories.jd_cache_repository import JDCacheRepository

    return JDCacheRepository()


def get_jd_cache_service():
    """Provide a JDCacheService with its dependencies."""
    from src.repositories.jd_cache_repository import JDCacheRepository
    from src.services.jd_cache_service import JDCacheService

    return JDCacheService(cache_repo=JDCacheRepository(), redis_client=None)


def get_notification_subscription_repository():
    """Provide a NotificationSubscriptionRepository instance."""
    from src.repositories.notification_repository import NotificationSubscriptionRepository

    return NotificationSubscriptionRepository()


def get_notification_preferences_repository():
    """Provide a NotificationPreferencesRepository instance."""
    from src.repositories.notification_repository import NotificationPreferencesRepository

    return NotificationPreferencesRepository()


def get_push_notification_service():
    """Provide a PushNotificationService with its repository dependencies."""
    from src.repositories.notification_repository import (
        NotificationPreferencesRepository,
        NotificationSubscriptionRepository,
    )
    from src.services.push_notification_service import PushNotificationService

    return PushNotificationService(
        subscription_repo=NotificationSubscriptionRepository(),
        preferences_repo=NotificationPreferencesRepository(),
    )


async def enforce_usage_tier(
    user: User = Depends(get_current_user),
) -> None:
    """
    FastAPI dependency that enforces tier limits before LLM operations.

    Add this to any LLM-powered route: Depends(enforce_usage_tier).
    Runs before the route handler — rejected requests incur zero LLM cost.
    """
    from src.db.documents.usage_ledger import UsageTier

    if getattr(user, "is_admin", False):
        user_tier = UsageTier.ADMIN
    elif getattr(user, "usage_tier", None) == "pro":
        user_tier = UsageTier.PRO
    else:
        user_tier = UsageTier.FREE
    service = get_usage_service()
    await service.enforce_tier_limit(user.id, user_tier)
