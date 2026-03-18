"""
GCC career ladder service — career progression framework for Global Capability Centers.

Pure-Python deterministic service that maps career levels, compensation
bands, and growth paths within India's GCC (Global Capability Center)
ecosystem. No LLM calls.
"""

from pydantic import BaseModel, Field


class GCCLevel(BaseModel):
    """A single level in the GCC career ladder."""

    level: str  # e.g., "IC1", "IC2", "M1"
    title: str
    years_experience_range: str  # e.g., "0-2"
    compensation_range_inr: str  # e.g., "8-15 LPA"
    key_expectations: list[str] = Field(default_factory=list)
    skills_required: list[str] = Field(default_factory=list)
    promotion_criteria: list[str] = Field(default_factory=list)


class GCCCareerPath(BaseModel):
    """A career path within a GCC."""

    track: str  # "individual_contributor" or "management"
    levels: list[GCCLevel] = Field(default_factory=list)
    transition_points: list[str] = Field(default_factory=list)  # where you can switch tracks


class GCCCompanyInsight(BaseModel):
    """Insights about a specific GCC type."""

    gcc_type: str  # "faang", "financial", "enterprise", "startup"
    characteristics: list[str] = Field(default_factory=list)
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)
    typical_compensation_premium: str = ""  # vs service companies


class GCCCareerAnalysis(BaseModel):
    """Complete GCC career analysis for a user."""

    current_level: str
    recommended_next_level: str
    ic_path: GCCCareerPath
    management_path: GCCCareerPath
    gcc_insights: list[GCCCompanyInsight] = Field(default_factory=list)
    growth_recommendations: list[str] = Field(default_factory=list)


# IC track levels
_IC_LEVELS = [
    GCCLevel(
        level="IC1",
        title="Software Engineer",
        years_experience_range="0-2",
        compensation_range_inr="8-18 LPA",
        key_expectations=["Write clean code", "Complete assigned tasks", "Learn codebase"],
        skills_required=["DSA fundamentals", "One programming language", "Git basics"],
        promotion_criteria=["Consistent delivery", "Code review participation", "Growing independence"],
    ),
    GCCLevel(
        level="IC2",
        title="Senior Software Engineer",
        years_experience_range="2-5",
        compensation_range_inr="18-35 LPA",
        key_expectations=["Own features end-to-end", "Mentor juniors", "Design reviews"],
        skills_required=["System design basics", "Testing expertise", "Cross-team collaboration"],
        promotion_criteria=["Technical leadership on projects", "Mentoring impact", "Design doc quality"],
    ),
    GCCLevel(
        level="IC3",
        title="Staff Engineer",
        years_experience_range="5-8",
        compensation_range_inr="35-60 LPA",
        key_expectations=["Drive technical direction", "Cross-team architecture", "Set best practices"],
        skills_required=["Advanced system design", "Technical strategy", "Organizational influence"],
        promotion_criteria=["Org-wide technical impact", "Architecture decisions", "Engineering culture"],
    ),
    GCCLevel(
        level="IC4",
        title="Principal Engineer",
        years_experience_range="8-12+",
        compensation_range_inr="60-100+ LPA",
        key_expectations=["Define technical vision", "Influence company strategy", "Industry thought leadership"],
        skills_required=["Strategic thinking", "Business acumen", "Innovation leadership"],
        promotion_criteria=["Company-wide impact", "Industry recognition", "Technical strategy ownership"],
    ),
]

# Management track levels
_MANAGEMENT_LEVELS = [
    GCCLevel(
        level="M1",
        title="Engineering Manager",
        years_experience_range="5-8",
        compensation_range_inr="30-55 LPA",
        key_expectations=["Lead team of 5-8", "Performance management", "Project delivery"],
        skills_required=["People management", "Project planning", "Stakeholder communication"],
        promotion_criteria=["Team health metrics", "Delivery track record", "Talent development"],
    ),
    GCCLevel(
        level="M2",
        title="Senior Engineering Manager",
        years_experience_range="8-12",
        compensation_range_inr="50-85 LPA",
        key_expectations=["Lead multiple teams", "Org-level strategy", "Hiring and culture"],
        skills_required=["Org design", "Strategic planning", "Cross-functional leadership"],
        promotion_criteria=["Org-level impact", "Leadership pipeline", "Strategic initiatives"],
    ),
    GCCLevel(
        level="M3",
        title="Director of Engineering",
        years_experience_range="12+",
        compensation_range_inr="80-150+ LPA",
        key_expectations=["Define engineering strategy", "Executive stakeholder management", "P&L awareness"],
        skills_required=["Executive communication", "Business strategy", "Org transformation"],
        promotion_criteria=["Business impact", "Executive presence", "Strategic vision"],
    ),
]

# GCC type insights
_GCC_INSIGHTS = [
    GCCCompanyInsight(
        gcc_type="faang",
        characteristics=["High engineering bar", "Strong IC track", "Global mobility"],
        pros=["Top compensation", "World-class engineering culture", "Resume brand value"],
        cons=["Intense interview process", "High performance pressure", "Role can be narrow"],
        typical_compensation_premium="80-150% over service companies",
    ),
    GCCCompanyInsight(
        gcc_type="financial",
        characteristics=["Strong compliance focus", "Stable work", "Domain expertise valued"],
        pros=["Good work-life balance", "Strong benefits", "Job stability"],
        cons=["Slower tech adoption", "More process overhead", "Limited IC growth path"],
        typical_compensation_premium="50-100% over service companies",
    ),
    GCCCompanyInsight(
        gcc_type="enterprise",
        characteristics=["Large scale systems", "Diverse tech stack", "Cross-geo collaboration"],
        pros=["Broad exposure", "International opportunities", "Structured growth"],
        cons=["Can be bureaucratic", "Legacy systems", "Slower promotion cycles"],
        typical_compensation_premium="40-80% over service companies",
    ),
    GCCCompanyInsight(
        gcc_type="startup",
        characteristics=["Fast-paced", "High ownership", "Equity potential"],
        pros=["Rapid growth opportunities", "Direct impact", "Modern tech stack"],
        cons=["Job instability", "Less structure", "Compensation may be lower base"],
        typical_compensation_premium="30-60% over service companies (excluding equity)",
    ),
]


def analyze_gcc_career(
    current_role: str,
    years_experience: float,
    target_track: str = "individual_contributor",
) -> GCCCareerAnalysis:
    """Analyze career progression within the GCC framework."""
    current_level = _determine_level(years_experience, target_track)
    next_level = _get_next_level(current_level, target_track)

    ic_path = GCCCareerPath(
        track="individual_contributor",
        levels=_IC_LEVELS,
        transition_points=["IC2 (can switch to M1)", "IC3 (can switch to M2)"],
    )

    mgmt_path = GCCCareerPath(
        track="management",
        levels=_MANAGEMENT_LEVELS,
        transition_points=["M1 (can switch back to IC3)", "M2 (can switch to IC4)"],
    )

    recommendations = _generate_recommendations(
        current_level, next_level, years_experience, target_track
    )

    return GCCCareerAnalysis(
        current_level=current_level,
        recommended_next_level=next_level,
        ic_path=ic_path,
        management_path=mgmt_path,
        gcc_insights=_GCC_INSIGHTS,
        growth_recommendations=recommendations,
    )


def get_gcc_level_details(level: str) -> GCCLevel | None:
    """Get details for a specific GCC level."""
    all_levels = _IC_LEVELS + _MANAGEMENT_LEVELS
    for l in all_levels:
        if l.level.lower() == level.lower():
            return l
    return None


def get_compensation_range(level: str) -> str:
    """Get compensation range for a level."""
    details = get_gcc_level_details(level)
    return details.compensation_range_inr if details else "Not available"


def _determine_level(years: float, track: str) -> str:
    """Determine current level based on experience."""
    if track == "management":
        if years >= 12:
            return "M3"
        if years >= 8:
            return "M2"
        if years >= 5:
            return "M1"
        return "IC2"  # Not yet management-ready

    # IC track
    if years >= 8:
        return "IC4"
    if years >= 5:
        return "IC3"
    if years >= 2:
        return "IC2"
    return "IC1"


def _get_next_level(current: str, track: str) -> str:
    """Get the recommended next level."""
    ic_progression = {"IC1": "IC2", "IC2": "IC3", "IC3": "IC4", "IC4": "IC4"}
    mgmt_progression = {"M1": "M2", "M2": "M3", "M3": "M3", "IC2": "M1"}

    if track == "management":
        return mgmt_progression.get(current, "M1")
    return ic_progression.get(current, "IC2")


def _generate_recommendations(
    current: str, next_level: str, years: float, track: str
) -> list[str]:
    """Generate growth recommendations based on current state."""
    recs = []

    if current == next_level:
        recs.append(f"You're at the top of the {track} track — consider mentoring or thought leadership.")
    else:
        details = get_gcc_level_details(next_level)
        if details:
            recs.append(f"Target {next_level} ({details.title}): focus on {', '.join(details.promotion_criteria[:2])}.")
            recs.append(f"Key skills to develop: {', '.join(details.skills_required[:3])}.")

    if track == "individual_contributor" and years >= 5:
        recs.append("Consider if the management track aligns with your goals — IC3/M1 is a common switch point.")

    if current in ("IC1", "IC2"):
        recs.append("Build a portfolio of impactful projects to demonstrate readiness for the next level.")

    return recs
