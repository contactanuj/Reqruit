"""
Tests for MongoDB document model schemas.

These tests validate document models WITHOUT a running MongoDB instance.
They verify:
- Field types and default values
- Enum validation (invalid values rejected)
- Embedded sub-model structure
- Index definitions are present
- Collection names are correct

No database connection is needed — we are testing Pydantic model behavior,
not Beanie's database operations. This keeps unit tests fast and CI-friendly.
"""


from beanie import PydanticObjectId

from src.db.documents.application import Application
from src.db.documents.company import Company
from src.db.documents.contact import Contact
from src.db.documents.document_record import DocumentRecord
from src.db.documents.embedded import SalaryRange
from src.db.documents.enums import (
    ApplicationStatus,
    DocumentType,
    InterviewType,
    MessageType,
    MockSessionStatus,
    RemotePreference,
)
from src.db.documents.interview import Interview, InterviewNotes
from src.db.documents.job import Job, JobRequirements
from src.db.documents.llm_usage import LLMUsage
from src.db.documents.mock_session import MockInterviewSession, QuestionFeedback
from src.db.documents.outreach_message import OutreachMessage
from src.db.documents.profile import Profile, UserPreferences
from src.db.documents.resume import (
    ContactInfo,
    Education,
    ParsedResumeData,
    Resume,
    WorkExperience,
)
from src.db.documents.star_story import STARStory
from src.db.documents.user import User

# ---------------------------------------------------------------------------
# Collection name tests — verify each model maps to the right collection
# ---------------------------------------------------------------------------


class TestCollectionNames:
    """Each document model should map to its expected MongoDB collection."""

    def test_user_collection(self) -> None:
        assert User.Settings.name == "users"

    def test_profile_collection(self) -> None:
        assert Profile.Settings.name == "profiles"

    def test_resume_collection(self) -> None:
        assert Resume.Settings.name == "resumes"

    def test_job_collection(self) -> None:
        assert Job.Settings.name == "jobs"

    def test_company_collection(self) -> None:
        assert Company.Settings.name == "companies"

    def test_contact_collection(self) -> None:
        assert Contact.Settings.name == "contacts"

    def test_application_collection(self) -> None:
        assert Application.Settings.name == "applications"

    def test_document_record_collection(self) -> None:
        assert DocumentRecord.Settings.name == "documents"

    def test_outreach_message_collection(self) -> None:
        assert OutreachMessage.Settings.name == "outreach_messages"

    def test_interview_collection(self) -> None:
        assert Interview.Settings.name == "interviews"

    def test_star_story_collection(self) -> None:
        assert STARStory.Settings.name == "star_stories"

    def test_llm_usage_collection(self) -> None:
        assert LLMUsage.Settings.name == "llm_usage"


# ---------------------------------------------------------------------------
# Default value tests — verify fields have sensible defaults
# ---------------------------------------------------------------------------


class TestUserDefaults:
    """User document should have correct defaults."""

    def test_is_active_defaults_to_true(self) -> None:
        user = User(email="test@example.com", hashed_password="hash123")
        assert user.is_active is True

    def test_schema_version_defaults_to_one(self) -> None:
        user = User(email="test@example.com", hashed_password="hash123")
        assert user.schema_version == 1

    def test_timestamps_default_to_none(self) -> None:
        user = User(email="test@example.com", hashed_password="hash123")
        assert user.created_at is None
        assert user.updated_at is None


class TestProfileDefaults:
    """Profile document should have correct defaults."""

    def test_empty_lists_default(self) -> None:
        user_id = PydanticObjectId()
        profile = Profile(user_id=user_id)
        assert profile.skills == []
        assert profile.target_roles == []

    def test_preferences_default(self) -> None:
        user_id = PydanticObjectId()
        profile = Profile(user_id=user_id)
        assert isinstance(profile.preferences, UserPreferences)
        assert profile.preferences.remote_preference == RemotePreference.NO_PREFERENCE
        assert profile.preferences.preferred_locations == []


class TestApplicationDefaults:
    """Application document should have correct defaults."""

    def test_status_defaults_to_saved(self) -> None:
        app = Application(
            user_id=PydanticObjectId(),
            job_id=PydanticObjectId(),
        )
        assert app.status == ApplicationStatus.SAVED

    def test_match_score_defaults_to_none(self) -> None:
        app = Application(
            user_id=PydanticObjectId(),
            job_id=PydanticObjectId(),
        )
        assert app.match_score is None


# ---------------------------------------------------------------------------
# Embedded sub-model tests
# ---------------------------------------------------------------------------


class TestEmbeddedModels:
    """Embedded sub-models should serialize correctly."""

    def test_salary_range_defaults(self) -> None:
        salary = SalaryRange()
        assert salary.min_amount == 0
        assert salary.max_amount == 0
        assert salary.currency == "USD"

    def test_salary_range_with_values(self) -> None:
        salary = SalaryRange(min_amount=100000, max_amount=150000, currency="EUR")
        assert salary.min_amount == 100000
        assert salary.currency == "EUR"

    def test_job_requirements_defaults(self) -> None:
        reqs = JobRequirements()
        assert reqs.required_skills == []
        assert reqs.preferred_skills == []
        assert reqs.experience_years is None

    def test_parsed_resume_data_defaults(self) -> None:
        parsed = ParsedResumeData()
        assert isinstance(parsed.contact_info, ContactInfo)
        assert parsed.work_experience == []
        assert parsed.education == []
        assert parsed.skills == []

    def test_work_experience_fields(self) -> None:
        exp = WorkExperience(
            company="Acme Corp",
            title="Senior Engineer",
            highlights=["Built API", "Led team"],
        )
        assert exp.company == "Acme Corp"
        assert len(exp.highlights) == 2

    def test_education_fields(self) -> None:
        edu = Education(
            institution="MIT",
            degree="B.S.",
            field_of_study="Computer Science",
        )
        assert edu.institution == "MIT"
        assert edu.degree == "B.S."

    def test_interview_notes_defaults(self) -> None:
        notes = InterviewNotes()
        assert notes.key_points == []
        assert notes.follow_up_items == []

    def test_user_preferences_with_salary(self) -> None:
        prefs = UserPreferences(
            target_salary=SalaryRange(min_amount=120000, max_amount=160000),
            preferred_locations=["San Francisco", "New York"],
            remote_preference=RemotePreference.REMOTE,
        )
        assert prefs.target_salary.min_amount == 120000
        assert len(prefs.preferred_locations) == 2
        assert prefs.remote_preference == RemotePreference.REMOTE


# ---------------------------------------------------------------------------
# Enum validation tests
# ---------------------------------------------------------------------------


class TestEnumValues:
    """Enums should have the expected values and serialize to strings."""

    def test_application_status_values(self) -> None:
        expected = {"saved", "applied", "interviewing", "offered",
                    "accepted", "rejected", "withdrawn"}
        actual = {s.value for s in ApplicationStatus}
        assert actual == expected

    def test_document_type_values(self) -> None:
        expected = {"cover_letter", "tailored_resume", "outreach_message"}
        actual = {t.value for t in DocumentType}
        assert actual == expected

    def test_message_type_values(self) -> None:
        expected = {"recruiter", "engineer", "manager", "generic"}
        actual = {t.value for t in MessageType}
        assert actual == expected

    def test_interview_type_values(self) -> None:
        expected = {"phone_screen", "technical", "behavioral",
                    "system_design", "final"}
        actual = {t.value for t in InterviewType}
        assert actual == expected

    def test_application_status_serializes_to_string(self) -> None:
        """StrEnum values should serialize to plain strings, not enum objects."""
        assert str(ApplicationStatus.SAVED) == "saved"
        assert ApplicationStatus.APPLIED == "applied"


# ---------------------------------------------------------------------------
# Document construction tests — verify models accept valid data
# ---------------------------------------------------------------------------


class TestDocumentConstruction:
    """Documents should be constructable with valid field values."""

    def test_job_with_embedded_models(self) -> None:
        job = Job(
            title="Senior Backend Engineer",
            company_name="Acme Corp",
            description="Build scalable APIs",
            requirements=JobRequirements(
                required_skills=["Python", "FastAPI"],
                experience_years=5,
            ),
            salary=SalaryRange(min_amount=150000, max_amount=200000),
            location="San Francisco, CA",
            remote=True,
        )
        assert job.title == "Senior Backend Engineer"
        assert len(job.requirements.required_skills) == 2
        assert job.salary.min_amount == 150000
        assert job.remote is True

    def test_resume_with_parsed_data(self) -> None:
        resume = Resume(
            user_id=PydanticObjectId(),
            title="General Resume",
            raw_text="John Doe\nSoftware Engineer\n...",
            parsed_data=ParsedResumeData(
                contact_info=ContactInfo(name="John Doe", email="john@example.com"),
                skills=["Python", "Go", "Kubernetes"],
            ),
            is_master=True,
        )
        assert resume.parsed_data is not None
        assert resume.parsed_data.contact_info.name == "John Doe"
        assert len(resume.parsed_data.skills) == 3
        assert resume.is_master is True

    def test_star_story_with_tags(self) -> None:
        story = STARStory(
            user_id=PydanticObjectId(),
            title="Led database migration",
            situation="Legacy MySQL database causing performance issues",
            task="Migrate to PostgreSQL with zero downtime",
            action="Designed dual-write strategy with gradual cutover",
            result="Completed migration with 99.99% uptime, 3x query speedup",
            tags=["leadership", "databases", "migration"],
        )
        assert len(story.tags) == 3
        assert story.title == "Led database migration"

    def test_interview_with_notes(self) -> None:
        interview = Interview(
            user_id=PydanticObjectId(),
            application_id=PydanticObjectId(),
            interview_type=InterviewType.TECHNICAL,
            company_name="Acme Corp",
            notes=InterviewNotes(
                key_points=["Asked about system design"],
                follow_up_items=["Send portfolio link"],
            ),
            questions=["Design a URL shortener", "Explain CAP theorem"],
        )
        assert interview.interview_type == InterviewType.TECHNICAL
        assert len(interview.notes.key_points) == 1
        assert len(interview.questions) == 2

    def test_llm_usage_tracking(self) -> None:
        usage = LLMUsage(
            user_id=PydanticObjectId(),
            agent="cover_letter_writer",
            model="claude-sonnet-4-20250514",
            provider="anthropic",
            task_type="cover_letter",
            input_tokens=1500,
            output_tokens=800,
            total_tokens=2300,
            cost_usd=0.023,
            latency_ms=2400,
        )
        assert usage.agent == "cover_letter_writer"
        assert usage.cost_usd == 0.023
        assert usage.total_tokens == 2300

    def test_contact_defaults(self) -> None:
        contact = Contact(
            company_id=PydanticObjectId(),
            name="Jane Smith",
        )
        assert contact.contacted is False
        assert contact.contacted_at is None
        assert contact.role == ""

    def test_outreach_message_defaults(self) -> None:
        msg = OutreachMessage(
            user_id=PydanticObjectId(),
            application_id=PydanticObjectId(),
            contact_id=PydanticObjectId(),
        )
        assert msg.message_type == MessageType.GENERIC
        assert msg.is_sent is False

    def test_document_record_construction(self) -> None:
        doc = DocumentRecord(
            user_id=PydanticObjectId(),
            application_id=PydanticObjectId(),
            doc_type=DocumentType.COVER_LETTER,
            content="Dear Hiring Manager...",
        )
        assert doc.doc_type == DocumentType.COVER_LETTER
        assert doc.is_approved is False
        assert doc.version == 1


# ---------------------------------------------------------------------------
# Index definition tests — verify indexes are declared
# ---------------------------------------------------------------------------


class TestIndexDefinitions:
    """Document models with compound indexes should have them declared."""

    def test_resume_has_user_master_index(self) -> None:
        index_names = [idx.document.get("name") for idx in Resume.Settings.indexes]
        assert "user_master_idx" in index_names

    def test_application_has_user_status_index(self) -> None:
        index_names = [idx.document.get("name") for idx in Application.Settings.indexes]
        assert "user_status_idx" in index_names

    def test_application_has_job_index(self) -> None:
        index_names = [idx.document.get("name") for idx in Application.Settings.indexes]
        assert "job_idx" in index_names

    def test_job_has_location_remote_index(self) -> None:
        index_names = [idx.document.get("name") for idx in Job.Settings.indexes]
        assert "location_remote_idx" in index_names

    def test_mock_session_has_user_interview_index(self) -> None:
        index_names = [idx.document.get("name") for idx in MockInterviewSession.Settings.indexes]
        assert "user_interview_idx" in index_names

    def test_star_story_has_tags_index(self) -> None:
        index_names = [idx.document.get("name") for idx in STARStory.Settings.indexes]
        assert "tags_idx" in index_names

    def test_llm_usage_has_agent_model_index(self) -> None:
        index_names = [idx.document.get("name") for idx in LLMUsage.Settings.indexes]
        assert "agent_model_idx" in index_names

    def test_document_record_has_user_doctype_index(self) -> None:
        index_names = [
            idx.document.get("name") for idx in DocumentRecord.Settings.indexes
        ]
        assert "user_doctype_idx" in index_names


# ---------------------------------------------------------------------------
# ALL_DOCUMENT_MODELS registry test
# ---------------------------------------------------------------------------


class TestDocumentRegistry:
    """ALL_DOCUMENT_MODELS should contain exactly the expected document classes."""

    def test_all_models_count(self) -> None:
        from src.db.documents import ALL_DOCUMENT_MODELS
        assert len(ALL_DOCUMENT_MODELS) == 38

    def test_all_models_are_unique(self) -> None:
        from src.db.documents import ALL_DOCUMENT_MODELS
        assert len(set(ALL_DOCUMENT_MODELS)) == 38

    def test_all_expected_models_present(self) -> None:
        from src.db.documents import ALL_DOCUMENT_MODELS
        from src.db.documents.application_success_tracker import (
            ApplicationSuccessTracker,
        )
        from src.db.documents.calendar_signal import CalendarSignal
        from src.db.documents.career_vitals import CareerVitals
        from src.db.documents.data_source_health import DataSourceHealth
        from src.db.documents.email_signal import EmailSignal
        from src.db.documents.integration_connection import IntegrationConnection
        from src.db.documents.interview_performance import InterviewPerformance
        from src.db.documents.jd_analysis_cache import JDAnalysisCache
        from src.db.documents.job_shortlist import JobShortlist
        from src.db.documents.notification_preferences import NotificationPreferences
        from src.db.documents.notification_subscription import NotificationSubscription
        from src.db.documents.market_config import MarketConfig
        from src.db.documents.market_signal import MarketSignal
        from src.db.documents.negotiation_session import NegotiationSession
        from src.db.documents.nudge import Nudge
        from src.db.documents.offer import Offer
        from src.db.documents.onboarding_plan import OnboardingPlan
        from src.db.documents.refresh_token import RefreshToken
        from src.db.documents.salary_benchmark import SalaryBenchmark
        from src.db.documents.scam_report import ScamReport
        from src.db.documents.skills_profile import SkillsProfile
        from src.db.documents.task_record import TaskRecord
        from src.db.documents.usage_ledger import UsageLedger
        from src.db.documents.user_activity import UserActivity
        from src.db.documents.variable_pay_benchmark import VariablePayBenchmark
        expected = {
            User, Profile, Resume, Job, Company, Contact,
            Application, DocumentRecord, OutreachMessage,
            Interview, STARStory, LLMUsage, MockInterviewSession,
            RefreshToken, MarketConfig, SkillsProfile,
            InterviewPerformance, ApplicationSuccessTracker,
            # Phase 3: Negotiation War Room
            Offer, SalaryBenchmark, NegotiationSession,
            VariablePayBenchmark,
            # Phase 4: Trust & Safety
            ScamReport,
            # Phase 4: Gamification
            UserActivity,
            # Phase 5: Career Operating System
            OnboardingPlan,
            # Phase 6: Career Health & Market Intelligence
            CareerVitals, MarketSignal,
            # Phase 6: Platform Maturity
            TaskRecord, UsageLedger, IntegrationConnection, EmailSignal,
            CalendarSignal,
            Nudge,
            DataSourceHealth,
            JobShortlist,
            JDAnalysisCache,
            NotificationPreferences,
            NotificationSubscription,
        }
        assert set(ALL_DOCUMENT_MODELS) == expected


# ---------------------------------------------------------------------------
# MockInterviewSession document tests
# ---------------------------------------------------------------------------


class TestMockInterviewSessionDocument:
    """Tests for MockInterviewSession document and QuestionFeedback embedded model."""

    def test_mock_session_collection(self) -> None:
        assert MockInterviewSession.Settings.name == "mock_sessions"

    def test_mock_session_defaults(self) -> None:
        session = MockInterviewSession(
            user_id=PydanticObjectId(),
            interview_id=PydanticObjectId(),
        )
        assert session.status == MockSessionStatus.IN_PROGRESS
        assert session.question_feedbacks == []
        assert session.current_question_index == 0
        assert session.overall_feedback == ""
        assert session.overall_score is None

    def test_mock_session_with_feedbacks(self) -> None:
        feedback = QuestionFeedback(
            question="Tell me about...",
            user_answer="I once...",
            ai_feedback="Good answer.",
            score=7,
        )
        session = MockInterviewSession(
            user_id=PydanticObjectId(),
            interview_id=PydanticObjectId(),
            question_feedbacks=[feedback],
            current_question_index=1,
        )
        assert len(session.question_feedbacks) == 1
        assert session.question_feedbacks[0].score == 7

    def test_question_feedback_defaults(self) -> None:
        feedback = QuestionFeedback()
        assert feedback.question == ""
        assert feedback.user_answer == ""
        assert feedback.ai_feedback == ""
        assert feedback.score is None

    def test_mock_session_status_values(self) -> None:
        assert MockSessionStatus.IN_PROGRESS == "in_progress"
        assert MockSessionStatus.COMPLETED == "completed"
        assert MockSessionStatus.ABANDONED == "abandoned"
