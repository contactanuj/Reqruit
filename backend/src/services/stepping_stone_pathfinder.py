"""
Stepping stone pathfinder — identifies bridge roles for career transitions.

Pure-Python deterministic service that maps intermediate roles between
a user's current position and their target role. No LLM calls.
"""

from pydantic import BaseModel, Field


class BridgeRole(BaseModel):
    """An intermediate role that bridges current and target positions."""

    title: str
    relevance_score: float  # 0-100
    skills_gained: list[str] = Field(default_factory=list)
    typical_duration_months: int = 18
    why_it_helps: str = ""
    risk_level: str = "medium"  # low, medium, high


class SteppingStoneResult(BaseModel):
    """Career path analysis with bridge roles."""

    current_role: str
    target_role: str
    direct_transition_feasibility: float  # 0-100
    bridge_roles: list[BridgeRole] = Field(default_factory=list)
    skills_to_acquire: list[str] = Field(default_factory=list)
    estimated_timeline_months: int = 0
    recommended_path: str = ""


# Role transition maps: (current_category, target_category) -> list of bridge roles
_BRIDGE_ROLES: dict[tuple[str, str], list[dict]] = {
    ("backend", "ml_engineer"): [
        {
            "title": "Data Engineer",
            "relevance_score": 85,
            "skills_gained": ["data pipelines", "ETL", "big data tools", "feature engineering"],
            "typical_duration_months": 12,
            "why_it_helps": "Builds data infrastructure skills essential for ML systems",
            "risk_level": "low",
        },
        {
            "title": "ML Platform Engineer",
            "relevance_score": 90,
            "skills_gained": ["MLOps", "model serving", "experiment tracking"],
            "typical_duration_months": 18,
            "why_it_helps": "Combines backend skills with ML infrastructure knowledge",
            "risk_level": "low",
        },
    ],
    ("backend", "engineering_manager"): [
        {
            "title": "Tech Lead",
            "relevance_score": 95,
            "skills_gained": ["technical leadership", "architecture decisions", "mentoring"],
            "typical_duration_months": 18,
            "why_it_helps": "Natural stepping stone that adds leadership to technical depth",
            "risk_level": "low",
        },
        {
            "title": "Staff Engineer",
            "relevance_score": 80,
            "skills_gained": ["cross-team influence", "technical strategy", "stakeholder management"],
            "typical_duration_months": 24,
            "why_it_helps": "Builds organizational influence before formal management",
            "risk_level": "medium",
        },
    ],
    ("frontend", "fullstack"): [
        {
            "title": "Frontend Developer with API Integration",
            "relevance_score": 85,
            "skills_gained": ["REST API design", "database basics", "server-side rendering"],
            "typical_duration_months": 6,
            "why_it_helps": "Gradually introduces backend concepts through frontend work",
            "risk_level": "low",
        },
    ],
    ("individual_contributor", "product_manager"): [
        {
            "title": "Technical Product Owner",
            "relevance_score": 90,
            "skills_gained": ["backlog management", "stakeholder communication", "prioritization"],
            "typical_duration_months": 12,
            "why_it_helps": "Bridges technical and product thinking",
            "risk_level": "medium",
        },
        {
            "title": "Developer Advocate",
            "relevance_score": 70,
            "skills_gained": ["communication", "user empathy", "product feedback loops"],
            "typical_duration_months": 12,
            "why_it_helps": "Builds external-facing and user-centric skills",
            "risk_level": "medium",
        },
    ],
    ("service_company", "product_company"): [
        {
            "title": "Product-Focused Service Role",
            "relevance_score": 75,
            "skills_gained": ["product thinking", "ownership mindset", "feature delivery"],
            "typical_duration_months": 12,
            "why_it_helps": "Build product skills within service company before transitioning",
            "risk_level": "low",
        },
        {
            "title": "Startup Engineer",
            "relevance_score": 85,
            "skills_gained": ["full ownership", "product sense", "rapid iteration"],
            "typical_duration_months": 18,
            "why_it_helps": "Smaller company gives breadth needed for product roles",
            "risk_level": "medium",
        },
    ],
}

# Role category detection
_ROLE_CATEGORIES = {
    "backend": ["backend", "server", "api developer", "systems engineer"],
    "frontend": ["frontend", "front-end", "ui developer", "react developer"],
    "fullstack": ["fullstack", "full-stack", "full stack"],
    "ml_engineer": ["ml engineer", "machine learning", "ai engineer", "data scientist"],
    "engineering_manager": ["engineering manager", "em", "dev manager"],
    "product_manager": ["product manager", "pm", "product owner"],
    "individual_contributor": ["software engineer", "developer", "sde", "programmer"],
    "service_company": ["consultant", "service", "tcs", "infosys", "wipro", "hcl", "cognizant"],
    "product_company": ["product engineer", "product company"],
}


def find_bridge_roles(
    current_role: str,
    target_role: str,
    current_skills: list[str] | None = None,
) -> SteppingStoneResult:
    """Find bridge roles between current and target positions."""
    current_cat = _categorize_role(current_role)
    target_cat = _categorize_role(target_role)

    bridge_key = (current_cat, target_cat)
    bridges_data = _BRIDGE_ROLES.get(bridge_key, [])

    bridges = [BridgeRole(**b) for b in bridges_data]

    # Calculate direct transition feasibility
    if bridges:
        feasibility = max(30.0, 100.0 - len(bridges) * 20)
    elif current_cat == target_cat:
        feasibility = 90.0
    else:
        feasibility = 40.0

    # Identify skills to acquire
    skills_needed = set()
    for b in bridges:
        skills_needed.update(s.lower() for s in b.skills_gained)
    if current_skills:
        skills_needed -= {s.lower() for s in current_skills}

    # Estimate timeline
    if bridges:
        timeline = bridges[0].typical_duration_months
    elif feasibility >= 80:
        timeline = 6
    else:
        timeline = 24

    # Recommended path
    if feasibility >= 80:
        recommended = f"Direct transition from {current_role} to {target_role} is feasible."
    elif bridges:
        recommended = f"Consider transitioning through {bridges[0].title} before targeting {target_role}."
    else:
        recommended = f"Build skills gradually while exploring adjacent roles."

    return SteppingStoneResult(
        current_role=current_role,
        target_role=target_role,
        direct_transition_feasibility=feasibility,
        bridge_roles=bridges,
        skills_to_acquire=sorted(skills_needed),
        estimated_timeline_months=timeline,
        recommended_path=recommended,
    )


def _categorize_role(role: str) -> str:
    """Categorize a role string into a known category."""
    role_lower = role.lower()
    for category, keywords in _ROLE_CATEGORIES.items():
        if any(kw in role_lower for kw in keywords):
            return category
    return "individual_contributor"
