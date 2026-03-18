"""Tests for the MarketConfig document model and its embedded sub-models."""

from src.db.documents.market_config import (
    CompensationComponent,
    CompensationStructure,
    CulturalContext,
    HiringProcess,
    InfrastructureContext,
    JobPlatformConfig,
    LegalProvisions,
    MarketConfig,
    ResumeConventions,
)


class TestCompensationComponent:
    """Tests for CompensationComponent embedded model."""

    def test_create_with_all_fields(self) -> None:
        comp = CompensationComponent(
            name="Basic",
            percentage_of_ctc=40.0,
            description="Base salary",
            is_statutory=False,
        )
        assert comp.name == "Basic"
        assert comp.percentage_of_ctc == 40.0
        assert comp.description == "Base salary"
        assert comp.is_statutory is False

    def test_defaults(self) -> None:
        comp = CompensationComponent(name="Bonus")
        assert comp.percentage_of_ctc is None
        assert comp.description == ""
        assert comp.is_statutory is False


class TestCompensationStructure:
    """Tests for CompensationStructure embedded model."""

    def test_defaults(self) -> None:
        cs = CompensationStructure()
        assert cs.components == []
        assert cs.ppp_factor == 1.0
        assert cs.currency_code == "USD"
        assert cs.currency_symbol == "$"
        assert cs.numbering_system == "international"

    def test_indian_numbering(self) -> None:
        cs = CompensationStructure(
            currency_code="INR",
            currency_symbol="₹",
            numbering_system="indian",
            ppp_factor=22.0,
        )
        assert cs.numbering_system == "indian"
        assert cs.ppp_factor == 22.0


class TestHiringProcess:
    """Tests for HiringProcess embedded model."""

    def test_defaults(self) -> None:
        hp = HiringProcess()
        assert hp.notice_period_norm_days == 14
        assert hp.buyout_culture is False
        assert hp.channels == []

    def test_indian_norms(self) -> None:
        hp = HiringProcess(
            notice_period_norm_days=60,
            buyout_culture=True,
            channels=["Naukri", "LinkedIn"],
        )
        assert hp.notice_period_norm_days == 60
        assert hp.buyout_culture is True
        assert len(hp.channels) == 2


class TestResumeConventions:
    """Tests for ResumeConventions embedded model."""

    def test_defaults(self) -> None:
        rc = ResumeConventions()
        assert rc.include_photo is False
        assert rc.include_dob is False
        assert rc.include_declaration is False
        assert rc.expected_pages_min == 1
        assert rc.expected_pages_max == 2
        assert rc.paper_size == "letter"
        assert rc.expected_salary_field is False

    def test_indian_conventions(self) -> None:
        rc = ResumeConventions(
            include_declaration=True,
            expected_pages_max=3,
            paper_size="A4",
            expected_salary_field=True,
        )
        assert rc.include_declaration is True
        assert rc.paper_size == "A4"


class TestJobPlatformConfig:
    """Tests for JobPlatformConfig embedded model."""

    def test_create(self) -> None:
        jp = JobPlatformConfig(
            name="Naukri",
            base_url="https://www.naukri.com",
            supports_api=False,
            market_share_pct=45.0,
            recommended_for=["IT", "engineering"],
        )
        assert jp.name == "Naukri"
        assert jp.supports_api is False
        assert len(jp.recommended_for) == 2

    def test_defaults(self) -> None:
        jp = JobPlatformConfig(name="TestPlatform")
        assert jp.base_url == ""
        assert jp.supports_api is False
        assert jp.market_share_pct == 0.0
        assert jp.recommended_for == []


class TestLegalProvisions:
    """Tests for LegalProvisions embedded model."""

    def test_defaults(self) -> None:
        lp = LegalProvisions()
        assert lp.non_compete_enforceable is True
        assert lp.data_protection_law == ""
        assert lp.visa_requirements == []


class TestCulturalContext:
    """Tests for CulturalContext embedded model."""

    def test_defaults(self) -> None:
        cc = CulturalContext()
        assert cc.languages == []
        assert cc.formality_level == "moderate"
        assert cc.referral_importance == "moderate"


class TestInfrastructureContext:
    """Tests for InfrastructureContext embedded model."""

    def test_defaults(self) -> None:
        ic = InfrastructureContext()
        assert ic.connectivity_level == "high"
        assert ic.primary_messaging == "email"
        assert ic.payment_rails == []


class TestMarketConfig:
    """Tests for the MarketConfig document model."""

    def test_create_minimal(self) -> None:
        config = MarketConfig(region_code="US")
        assert config.region_code == "US"
        assert config.region_name == ""
        assert config.version == 1

    def test_create_full(self) -> None:
        config = MarketConfig(
            region_code="IN",
            region_name="India",
            compensation_structure=CompensationStructure(
                currency_code="INR",
                ppp_factor=22.0,
            ),
            hiring_process=HiringProcess(notice_period_norm_days=60),
            resume_conventions=ResumeConventions(paper_size="A4"),
            job_platforms=[JobPlatformConfig(name="Naukri")],
            legal=LegalProvisions(non_compete_enforceable=False),
            cultural=CulturalContext(languages=["English", "Hindi"]),
            infrastructure=InfrastructureContext(primary_messaging="WhatsApp"),
            version=1,
        )
        assert config.region_code == "IN"
        assert config.region_name == "India"
        assert config.compensation_structure.currency_code == "INR"
        assert config.hiring_process.notice_period_norm_days == 60
        assert len(config.job_platforms) == 1
        assert config.cultural.languages[0] == "English"

    def test_default_sub_models(self) -> None:
        config = MarketConfig(region_code="DE")
        assert isinstance(config.compensation_structure, CompensationStructure)
        assert isinstance(config.hiring_process, HiringProcess)
        assert isinstance(config.resume_conventions, ResumeConventions)
        assert config.job_platforms == []

    def test_collection_name(self) -> None:
        assert MarketConfig.Settings.name == "market_configs"

    def test_model_dump(self) -> None:
        config = MarketConfig(region_code="US", region_name="United States")
        data = config.model_dump()
        assert data["region_code"] == "US"
        assert data["region_name"] == "United States"
        assert "compensation_structure" in data
        assert "hiring_process" in data

    def test_version_defaults_to_one(self) -> None:
        config = MarketConfig(region_code="JP")
        assert config.version == 1
