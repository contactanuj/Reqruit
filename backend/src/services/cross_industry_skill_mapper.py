"""
Cross-industry skill mapper — translates skills between industries.

Pure-Python deterministic service that maps skills from one industry context
to another, identifying transferable skills and translation gaps.
No LLM calls.
"""

import re

from pydantic import BaseModel, Field


class SkillTranslation(BaseModel):
    """A single skill translated from source to target industry."""

    source_skill: str
    target_equivalent: str
    transferability: float  # 0.0-1.0
    context_shift: str  # how the skill is applied differently
    gap_to_close: str  # what additional learning is needed


class SkillTranslationResult(BaseModel):
    """Complete skill translation between industries."""

    source_industry: str
    target_industry: str
    translations: list[SkillTranslation] = Field(default_factory=list)
    highly_transferable: list[str] = Field(default_factory=list)
    needs_adaptation: list[str] = Field(default_factory=list)
    non_transferable: list[str] = Field(default_factory=list)
    overall_transferability: float = 0.0  # 0-100


# Universal skills that transfer across most industries
_UNIVERSAL_SKILLS = {
    "project management": ("Project Management", 0.95, "Same core skill, different domain terminology", "Learn industry-specific tools"),
    "communication": ("Communication", 0.95, "Adjust for industry jargon", "Learn domain vocabulary"),
    "leadership": ("Leadership", 0.90, "Team dynamics similar across industries", "Understand industry culture"),
    "data analysis": ("Data Analysis", 0.85, "Analysis methods transfer, data types differ", "Learn domain-specific datasets"),
    "problem solving": ("Problem Solving", 0.90, "Core skill transfers directly", "Learn domain constraints"),
    "python": ("Python", 0.80, "Language transfers, libraries differ by domain", "Learn domain-specific libraries"),
    "sql": ("SQL", 0.85, "Database skills transfer, schemas differ", "Learn domain data models"),
    "agile": ("Agile/Scrum", 0.85, "Framework transfers, ceremonies may differ", "Adapt to team conventions"),
    "testing": ("Testing/QA", 0.80, "Methods transfer, compliance requirements differ", "Learn domain test standards"),
}

# Industry-specific translation overrides
_TECH_TO_FINANCE = {
    "microservices": ("Distributed Systems", 0.70, "Similar architecture, stricter compliance", "Learn financial regulations and audit requirements"),
    "ci/cd": ("Release Management", 0.75, "Same concepts, more change control gates", "Learn CAB processes and regulatory approvals"),
    "devops": ("Site Reliability", 0.75, "Similar goals, higher availability requirements", "Learn financial SLA requirements"),
    "machine learning": ("Quantitative Modeling", 0.60, "Core ML transfers, domain models are specialized", "Learn financial modeling and risk frameworks"),
    "api design": ("API Design", 0.80, "Same principles, security-first approach", "Learn PCI-DSS and financial API standards"),
}

_TECH_TO_HEALTHCARE = {
    "microservices": ("Health IT Architecture", 0.65, "Similar patterns, HIPAA compliance required", "Learn HL7/FHIR standards and HIPAA"),
    "data engineering": ("Health Data Engineering", 0.70, "ETL transfers, data governance is stricter", "Learn EHR systems and health data standards"),
    "machine learning": ("Clinical AI/ML", 0.55, "Core ML transfers, clinical validation required", "Learn FDA regulations for AI/ML in healthcare"),
    "devops": ("Health IT Operations", 0.70, "Similar goals, compliance-heavy", "Learn HIPAA technical safeguards"),
}

_FINANCE_TO_TECH = {
    "risk modeling": ("Machine Learning", 0.60, "Statistical foundations transfer", "Learn modern ML frameworks and tooling"),
    "compliance automation": ("Policy-as-Code", 0.65, "Automation skills transfer directly", "Learn infrastructure-as-code tools"),
    "trading systems": ("Low-Latency Systems", 0.75, "Performance engineering transfers well", "Learn broader distributed systems patterns"),
}


def translate_skills(
    skills: list[str],
    source_industry: str,
    target_industry: str,
) -> SkillTranslationResult:
    """Translate a list of skills from one industry context to another."""
    translations = []
    highly_transferable = []
    needs_adaptation = []
    non_transferable = []

    # Get industry-specific map
    industry_map = _get_industry_map(source_industry, target_industry)

    for skill in skills:
        skill_lower = skill.lower().strip()

        # Check industry-specific translation first
        if skill_lower in industry_map:
            equiv, transfer, context, gap = industry_map[skill_lower]
            translations.append(SkillTranslation(
                source_skill=skill,
                target_equivalent=equiv,
                transferability=transfer,
                context_shift=context,
                gap_to_close=gap,
            ))
        elif skill_lower in _UNIVERSAL_SKILLS:
            equiv, transfer, context, gap = _UNIVERSAL_SKILLS[skill_lower]
            translations.append(SkillTranslation(
                source_skill=skill,
                target_equivalent=equiv,
                transferability=transfer,
                context_shift=context,
                gap_to_close=gap,
            ))
        else:
            # Default: assume moderate transferability
            translations.append(SkillTranslation(
                source_skill=skill,
                target_equivalent=skill,
                transferability=0.5,
                context_shift=f"May require adaptation for {target_industry} context",
                gap_to_close=f"Research how {skill} is applied in {target_industry}",
            ))

    # Categorize
    for t in translations:
        if t.transferability >= 0.8:
            highly_transferable.append(t.source_skill)
        elif t.transferability >= 0.5:
            needs_adaptation.append(t.source_skill)
        else:
            non_transferable.append(t.source_skill)

    overall = (
        sum(t.transferability for t in translations) / len(translations) * 100
        if translations
        else 0.0
    )

    return SkillTranslationResult(
        source_industry=source_industry,
        target_industry=target_industry,
        translations=translations,
        highly_transferable=highly_transferable,
        needs_adaptation=needs_adaptation,
        non_transferable=non_transferable,
        overall_transferability=round(overall, 1),
    )


def _get_industry_map(
    source: str, target: str
) -> dict[str, tuple[str, float, str, str]]:
    """Get the industry-specific skill translation map."""
    source_lower = source.lower()
    target_lower = target.lower()

    if _is_tech(source_lower) and _is_finance(target_lower):
        return _TECH_TO_FINANCE
    if _is_tech(source_lower) and _is_healthcare(target_lower):
        return _TECH_TO_HEALTHCARE
    if _is_finance(source_lower) and _is_tech(target_lower):
        return _FINANCE_TO_TECH

    return {}


def _is_tech(industry: str) -> bool:
    return any(k in industry for k in ("tech", "software", "saas")) or bool(re.search(r'\bit\b', industry))


def _is_finance(industry: str) -> bool:
    return any(k in industry for k in ("finance", "banking", "fintech"))


def _is_healthcare(industry: str) -> bool:
    return any(k in industry for k in ("health", "pharma", "biotech", "medical"))
