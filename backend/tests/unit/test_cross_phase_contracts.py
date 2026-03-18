"""
Cross-phase contract tests — verify data flows across phase boundaries.

These tests validate that outputs from one phase match the expected inputs
of the next, without needing a running database. They catch schema drift
between phases early.

Phase chain:
  Profile (Phase 1) → Discovery (Phase 6) → Application (Phase 2)
  Application → Interview Prep (Phase 2) → Negotiation (Phase 3)
  Company trust signals (Phase 4) → Discovery scoring (Phase 6)
  Career Vitals (Phase 5) → Market Intelligence (Phase 5)
"""

from datetime import UTC, datetime

from beanie import PydanticObjectId

from src.db.documents.enums import ApplicationStatus, RemotePreference
from src.db.documents.profile import Profile, UserPreferences
from src.services.jd_cache_service import fingerprint, normalize_text

# ---------------------------------------------------------------------------
# Phase 1 → Phase 6: Profile feeds Discovery preferences
# ---------------------------------------------------------------------------


class TestProfileToDiscoveryContract:
    """Profile preferences must be compatible with discovery filtering."""

    def test_profile_preferences_have_discovery_fields(self):
        """UserPreferences must contain fields that discovery uses for matching."""
        prefs = UserPreferences(
            remote_preference=RemotePreference.REMOTE,
            preferred_locations=["San Francisco"],
        )
        # Discovery service reads these fields to filter jobs
        assert hasattr(prefs, "remote_preference")
        assert hasattr(prefs, "preferred_locations")
        assert isinstance(prefs.preferred_locations, list)

    def test_profile_target_roles_are_strings(self):
        """target_roles must be a list of strings for discovery role matching."""
        profile = Profile(
            user_id=PydanticObjectId(),
            target_roles=["Backend Engineer", "SRE"],
        )
        assert all(isinstance(r, str) for r in profile.target_roles)

    def test_profile_skills_are_strings(self):
        """skills must be a list of strings for JD matching."""
        profile = Profile(
            user_id=PydanticObjectId(),
            skills=["Python", "FastAPI", "MongoDB"],
        )
        assert all(isinstance(s, str) for s in profile.skills)


# ---------------------------------------------------------------------------
# Phase 6 → Phase 2: Discovery shortlist feeds Application
# ---------------------------------------------------------------------------


class TestDiscoveryToApplicationContract:
    """Shortlisted jobs must carry fields that Application needs."""

    def test_job_document_has_application_fields(self):
        """Job must have title, company_name, description for application assembly."""
        from src.db.documents.job import Job

        job = Job(
            title="Backend Engineer",
            company_name="Acme Corp",
            description="Build APIs",
        )
        # Application assembly workflow needs these
        assert job.title
        assert job.company_name
        assert job.description

    def test_application_references_job_by_id(self):
        """Application links to a Job via job_id (PydanticObjectId)."""
        from src.db.documents.application import Application

        app = Application(
            user_id=PydanticObjectId(),
            job_id=PydanticObjectId(),
        )
        assert isinstance(app.job_id, PydanticObjectId)
        assert app.status == ApplicationStatus.SAVED


# ---------------------------------------------------------------------------
# Phase 2 → Phase 3: Application outcome feeds Negotiation
# ---------------------------------------------------------------------------


class TestApplicationToNegotiationContract:
    """Offered applications must be compatible with negotiation session creation."""

    def test_application_offered_status_exists(self):
        """ApplicationStatus must include 'offered' for negotiation trigger."""
        assert hasattr(ApplicationStatus, "OFFERED")
        assert ApplicationStatus.OFFERED == "offered"

    def test_offer_document_has_negotiation_fields(self):
        """Offer must have salary fields that negotiation service reads."""
        from src.db.documents.offer import Offer

        offer = Offer(
            user_id=PydanticObjectId(),
            application_id=PydanticObjectId(),
            company_name="Acme",
            role_title="Senior Engineer",
            total_comp_annual=150000.0,
        )
        assert hasattr(offer, "total_comp_annual")
        assert hasattr(offer, "company_name")
        assert hasattr(offer, "role_title")
        assert isinstance(offer.total_comp_annual, (int, float))


# ---------------------------------------------------------------------------
# Phase 4 → Phase 6: Trust signals feed Discovery scoring
# ---------------------------------------------------------------------------


class TestTrustToDiscoveryContract:
    """Scam reports and company verification must be queryable by company."""

    def test_scam_report_has_company_name(self):
        """ScamReport must have company_name for cross-referencing during discovery."""
        from src.db.documents.scam_report import ScamReport

        report = ScamReport(
            reporter_user_id=PydanticObjectId(),
            entity_type="company",
            entity_identifier="Sketchy LLC",
            company_name="Sketchy LLC",
            reason="No domain, fake address",
        )
        assert report.entity_identifier == "Sketchy LLC"

    def test_data_source_health_has_status(self):
        """DataSourceHealth must have status for discovery source selection."""
        from src.db.documents.data_source_health import DataSourceHealth

        health = DataSourceHealth(
            source_name="indeed_api",
            status="healthy",
        )
        assert health.status == "healthy"
        assert hasattr(health, "disabled")


# ---------------------------------------------------------------------------
# Phase 5 → Phase 5: Career Vitals + Market Signals
# ---------------------------------------------------------------------------


class TestCareerToMarketContract:
    """CareerVitals must be compatible with market signal enrichment."""

    def test_career_vitals_has_user_id(self):
        """CareerVitals must have user_id for per-user market contextualization."""
        from src.db.documents.career_vitals import CareerVitals

        vitals = CareerVitals(
            user_id=PydanticObjectId(),
        )
        assert isinstance(vitals.user_id, PydanticObjectId)

    def test_market_signal_has_signal_type(self):
        """MarketSignal must have signal_type for filtering."""
        from src.db.documents.market_signal import MarketSignal

        signal = MarketSignal(
            signal_type="hiring_velocity",
            source="external_api",
            data={"velocity": 0.85},
        )
        assert signal.signal_type == "hiring_velocity"


# ---------------------------------------------------------------------------
# JD Fingerprinting contract: same text → same fingerprint
# ---------------------------------------------------------------------------


class TestJDFingerprintContract:
    """JD fingerprinting must be deterministic and normalization-stable."""

    def test_identical_text_same_fingerprint(self):
        fp1 = fingerprint("Senior Backend Engineer at Acme Corp")
        fp2 = fingerprint("Senior Backend Engineer at Acme Corp")
        assert fp1 == fp2

    def test_whitespace_variations_same_fingerprint(self):
        fp1 = fingerprint("Senior  Backend   Engineer")
        fp2 = fingerprint("  senior backend engineer  ")
        assert fp1 == fp2

    def test_different_jds_different_fingerprints(self):
        fp1 = fingerprint("Backend Engineer Python")
        fp2 = fingerprint("Frontend Engineer React")
        assert fp1 != fp2

    def test_normalize_is_idempotent(self):
        text = "  Hello   World  "
        assert normalize_text(normalize_text(text)) == normalize_text(text)


# ---------------------------------------------------------------------------
# Schema version contract: all documents inherit schema_version
# ---------------------------------------------------------------------------


class TestSchemaVersionContract:
    """All TimestampedDocument subclasses must have schema_version."""

    def test_all_documents_have_schema_version(self):
        from src.db.documents import ALL_DOCUMENT_MODELS

        for model in ALL_DOCUMENT_MODELS:
            instance = model.model_construct()
            if instance is not None:
                assert hasattr(instance, "schema_version"), (
                    f"{model.__name__} missing schema_version"
                )

    def test_schema_version_defaults_to_one(self):
        from src.db.documents.user import User

        user = User(email="test@example.com", hashed_password="hash")
        assert user.schema_version == 1


# ---------------------------------------------------------------------------
# Integration connection → Signal pipeline contract
# ---------------------------------------------------------------------------


class TestIntegrationToSignalContract:
    """Integration connections must produce signals with correct fields."""

    def test_email_signal_has_required_fields(self):
        from src.db.documents.email_signal import EmailSignal
        from src.db.documents.integration_connection import IntegrationProvider

        signal = EmailSignal(
            user_id=PydanticObjectId(),
            provider=IntegrationProvider.GMAIL,
            message_id="msg_123",
            sender_domain="acme.com",
            matched_pattern="interview_invitation",
            company_name="Acme Corp",
        )
        assert signal.sender_domain == "acme.com"
        assert signal.matched_pattern == "interview_invitation"
        assert signal.message_id == "msg_123"

    def test_calendar_signal_has_required_fields(self):
        from src.db.documents.calendar_signal import CalendarSignal
        from src.db.documents.integration_connection import IntegrationProvider

        signal = CalendarSignal(
            user_id=PydanticObjectId(),
            provider=IntegrationProvider.GOOGLE_CALENDAR,
            event_id="evt_456",
            company_name="Acme Corp",
            event_date=datetime.now(UTC),
        )
        assert signal.event_id == "evt_456"
        assert signal.company_name == "Acme Corp"
        assert signal.event_date is not None
