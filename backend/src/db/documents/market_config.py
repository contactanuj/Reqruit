"""
Market configuration document — one document per country/region.

MarketConfig stores all market-specific data that agents and services need
to produce locale-appropriate output: compensation structures, hiring norms,
resume conventions, job platforms, legal provisions, cultural context, and
infrastructure details.

Design decisions
----------------
Why one document per region (not per city or per industry):
    Country-level is the right granularity for hiring norms, legal provisions,
    and cultural context. City-level differences (e.g., metro vs non-metro
    HRA rates) are handled as parameters within the compensation structure,
    not as separate documents. Industry differences are handled by the
    career_sector field on UserLocaleProfile, not by duplicating MarketConfig.

Why so many embedded sub-models:
    Each sub-model groups a coherent set of market attributes. This keeps
    MarketConfig readable and lets services access only the subset they need.
    All sub-models are always accessed with their parent — they have no
    independent lifecycle.

Why region_code uses ISO 3166-1 alpha-2:
    Two-letter country codes (IN, US, AE, DE) are universally understood,
    compact for storage, and supported by every internationalization library.
"""

from beanie import Indexed
from pydantic import BaseModel
from pymongo import ASCENDING, IndexModel

from src.db.base_document import TimestampedDocument


# ---------------------------------------------------------------------------
# Embedded sub-models
# ---------------------------------------------------------------------------


class CompensationComponent(BaseModel):
    """Single component of a compensation structure (e.g., Basic, HRA, PF)."""

    name: str
    percentage_of_ctc: float | None = None
    description: str = ""
    is_statutory: bool = False


class CompensationStructure(BaseModel):
    """Market-specific compensation breakdown rules and PPP data."""

    components: list[CompensationComponent] = []
    ppp_factor: float = 1.0
    currency_code: str = "USD"
    currency_symbol: str = "$"
    numbering_system: str = "international"  # "indian" for lakh/crore


class HiringProcess(BaseModel):
    """Market-specific hiring norms."""

    notice_period_norm_days: int = 14
    buyout_culture: bool = False
    channels: list[str] = []


class ResumeConventions(BaseModel):
    """What a resume looks like in this market."""

    include_photo: bool = False
    include_dob: bool = False
    include_declaration: bool = False
    expected_pages_min: int = 1
    expected_pages_max: int = 2
    paper_size: str = "letter"
    expected_salary_field: bool = False


class JobPlatformConfig(BaseModel):
    """A job platform available in this market."""

    name: str
    base_url: str = ""
    supports_api: bool = False
    market_share_pct: float = 0.0
    recommended_for: list[str] = []


class LegalProvisions(BaseModel):
    """Legal context for employment in this market."""

    non_compete_enforceable: bool = True
    data_protection_law: str = ""
    worker_protections: str = ""
    visa_requirements: list[dict] = []


class CulturalContext(BaseModel):
    """Cultural norms relevant to job seeking and interviews."""

    languages: list[str] = []
    formality_level: str = "moderate"
    family_decision_involvement: str = "low"
    referral_importance: str = "moderate"
    interview_style: str = "standard"


class InfrastructureContext(BaseModel):
    """Infrastructure context affecting how the product is used."""

    connectivity_level: str = "high"
    primary_messaging: str = "email"
    payment_rails: list[str] = []
    identity_systems: list[str] = []


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------


class MarketConfig(TimestampedDocument):
    """
    Market-specific configuration — one document per country/region.

    Seed data for IN and US is loaded on application startup. Additional
    markets can be added via admin API without code changes.

    Fields:
        region_code: ISO 3166-1 alpha-2 country code. Unique indexed.
        region_name: Human-readable name (e.g., "India", "United States").
        compensation_structure: How compensation is structured in this market.
        hiring_process: Hiring norms (notice periods, channels).
        resume_conventions: What a resume looks like.
        job_platforms: Available job search platforms.
        legal: Employment law context.
        cultural: Cultural norms for job seeking.
        infrastructure: Tech infrastructure context.
        version: Incremented on each admin update for audit trail.
    """

    region_code: Indexed(str, unique=True)
    region_name: str = ""
    compensation_structure: CompensationStructure = CompensationStructure()
    hiring_process: HiringProcess = HiringProcess()
    resume_conventions: ResumeConventions = ResumeConventions()
    job_platforms: list[JobPlatformConfig] = []
    legal: LegalProvisions = LegalProvisions()
    cultural: CulturalContext = CulturalContext()
    infrastructure: InfrastructureContext = InfrastructureContext()
    version: int = 1

    class Settings:
        name = "market_configs"
        indexes = [
            IndexModel(
                [("region_code", ASCENDING)],
                name="region_code_idx",
                unique=True,
            ),
        ]
