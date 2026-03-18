"""
Beanie document models — each file defines one MongoDB collection.

Documents are Pydantic models, so the same class serves as:
  1. MongoDB document definition (schema, indexes, collection name)
  2. Validation rules (field types, constraints, defaults)
  3. API-compatible data structures (serializable to JSON)

ALL_DOCUMENT_MODELS is the list registered with init_beanie during startup.
Only concrete document classes go here — not the TimestampedDocument base.
"""

from src.db.documents.application import Application
from src.db.documents.application_success_tracker import ApplicationSuccessTracker
from src.db.documents.calendar_signal import CalendarSignal
from src.db.documents.career_vitals import CareerVitals
from src.db.documents.company import Company
from src.db.documents.contact import Contact
from src.db.documents.data_source_health import DataSourceHealth
from src.db.documents.document_record import DocumentRecord
from src.db.documents.email_signal import EmailSignal
from src.db.documents.jd_analysis_cache import JDAnalysisCache
from src.db.documents.integration_connection import IntegrationConnection
from src.db.documents.interview import Interview
from src.db.documents.interview_performance import InterviewPerformance
from src.db.documents.job import Job
from src.db.documents.job_shortlist import JobShortlist
from src.db.documents.llm_usage import LLMUsage
from src.db.documents.market_config import MarketConfig
from src.db.documents.market_signal import MarketSignal
from src.db.documents.mock_session import MockInterviewSession
from src.db.documents.negotiation_session import NegotiationSession
from src.db.documents.notification_preferences import NotificationPreferences
from src.db.documents.notification_subscription import NotificationSubscription
from src.db.documents.nudge import Nudge
from src.db.documents.offer import Offer
from src.db.documents.onboarding_plan import OnboardingPlan
from src.db.documents.outreach_message import OutreachMessage
from src.db.documents.profile import Profile
from src.db.documents.refresh_token import RefreshToken
from src.db.documents.resume import Resume
from src.db.documents.salary_benchmark import SalaryBenchmark
from src.db.documents.scam_report import ScamReport
from src.db.documents.skills_profile import SkillsProfile
from src.db.documents.star_story import STARStory
from src.db.documents.task_record import TaskRecord
from src.db.documents.usage_ledger import UsageLedger
from src.db.documents.user import User
from src.db.documents.user_activity import UserActivity
from src.db.documents.variable_pay_benchmark import VariablePayBenchmark

# All document classes registered with Beanie during init_beanie().
# Order does not matter — Beanie resolves dependencies internally.
ALL_DOCUMENT_MODELS: list[type] = [
    User,
    Profile,
    Resume,
    Job,
    Company,
    Contact,
    Application,
    DocumentRecord,
    OutreachMessage,
    Interview,
    STARStory,
    LLMUsage,
    MockInterviewSession,
    RefreshToken,
    # Phase 0: Locale & Market Context
    MarketConfig,
    # Phase 1: Professional Identity
    SkillsProfile,
    # Phase 2: Application Intelligence
    InterviewPerformance,
    ApplicationSuccessTracker,
    # Phase 3: Negotiation War Room
    SalaryBenchmark,
    Offer,
    NegotiationSession,
    VariablePayBenchmark,
    # Phase 4: Trust & Safety
    ScamReport,
    # Phase 4: Gamification
    UserActivity,
    # Phase 5: Career Operating System
    OnboardingPlan,
    CareerVitals,
    MarketSignal,
    # Phase 6: Platform Maturity
    TaskRecord,
    UsageLedger,
    IntegrationConnection,
    EmailSignal,
    CalendarSignal,
    Nudge,
    DataSourceHealth,
    JobShortlist,
    JDAnalysisCache,
    NotificationSubscription,
    NotificationPreferences,
]

__all__ = [
    "ALL_DOCUMENT_MODELS",
    "Application",
    "ApplicationSuccessTracker",
    "Company",
    "Contact",
    "DocumentRecord",
    "Interview",
    "InterviewPerformance",
    "Job",
    "LLMUsage",
    "MarketConfig",
    "MockInterviewSession",
    "Offer",
    "NegotiationSession",
    "SalaryBenchmark",
    "OutreachMessage",
    "Profile",
    "RefreshToken",
    "Resume",
    "SkillsProfile",
    "ScamReport",
    "STARStory",
    "User",
    "UserActivity",
    "IntegrationConnection",
    "EmailSignal",
    "CalendarSignal",
    "Nudge",
    "DataSourceHealth",
    "JDAnalysisCache",
    "JobShortlist",
    "OnboardingPlan",
    "CareerVitals",
    "MarketSignal",
    "TaskRecord",
    "NotificationPreferences",
    "NotificationSubscription",
    "UsageLedger",
]
