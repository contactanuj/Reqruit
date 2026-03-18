"""
LLM provider types, routing configuration, and cost constants.

This module defines the data structures that drive the ModelManager's behavior:
which model handles each task, what the fallback chain looks like, and how much
each model costs per token.

Design decisions
----------------
Why StrEnum for TaskType and ProviderName (not plain strings):
    Enums prevent typos ("cover_leter" vs "cover_letter") and provide IDE
    autocomplete. StrEnum serializes to plain strings in logs, MongoDB, and
    JSON — no special handling needed. This matches the pattern used in
    src/db/documents/enums.py for ApplicationStatus, DocumentType, etc.

Why a routing TABLE (not per-agent configuration):
    The routing table is a single source of truth for "task X uses model Y
    with fallback Z." Agents declare their task type; the table handles the
    rest. This separation means we can change models, add fallbacks, or
    adjust temperatures without touching any agent code.

    Alternative: each agent specifies its model directly. Works for 2-3
    agents but becomes inconsistent with 13 agents making independent
    choices. A centralized table ensures consistency and makes cost
    optimization visible in one place.

Why a flat cost table (not provider-specific pricing objects):
    Each model has exactly two numbers: input cost and output cost per
    million tokens. A flat dict keyed by model name is the simplest correct
    structure. If pricing becomes more complex (tiered, volume-based), we
    can refactor to a class hierarchy then.

Why dataclass for ModelConfig (not Pydantic BaseModel):
    ModelConfig is a plain data container used internally — it never crosses
    an API boundary, is never stored in MongoDB, and never needs validation
    beyond what Python's type system provides. A dataclass avoids Pydantic
    overhead and keeps the module dependency-free.
"""

from dataclasses import dataclass
from enum import StrEnum

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TaskType(StrEnum):
    """
    What the LLM call is for — determines which model gets used.

    Each agent maps its work to one of these task types. The ROUTING_TABLE
    below maps each task type to a prioritized list of model configurations.
    """

    COVER_LETTER = "cover_letter"
    RESUME_TAILORING = "resume_tailoring"
    JOB_MATCHING = "job_matching"
    COMPANY_RESEARCH = "company_research"
    QUICK_CHAT = "quick_chat"
    DATA_EXTRACTION = "data_extraction"
    INTERVIEW_PREP = "interview_prep"
    OUTREACH_MESSAGE = "outreach_message"
    RESUME_PARSING = "resume_parsing"
    STAR_STORY = "star_story"
    MOCK_INTERVIEW = "mock_interview"
    GENERAL = "general"

    # --- Phase 0: Locale & Market Context ---
    LOCALE_ADVISORY = "locale_advisory"
    COMPENSATION_ANALYSIS = "compensation_analysis"
    REGIONAL_RESUME = "regional_resume"
    SCAM_INTELLIGENCE = "scam_intelligence"
    VISA_NAVIGATION = "visa_navigation"
    CULTURAL_COACHING = "cultural_coaching"

    # --- Phase 1: Professional Identity ---
    ACHIEVEMENT_MINING = "achievement_mining"
    SKILLS_ANALYSIS = "skills_analysis"

    # --- Phase 2: Application Intelligence ---
    APPLICATION_ORCHESTRATION = "application_orchestration"
    SUCCESS_PATTERN = "success_pattern"
    INTERVIEW_COACHING = "interview_coaching"
    QUESTION_PREDICTION = "question_prediction"

    # --- Phase 3: Negotiation War Room ---
    OFFER_ANALYSIS = "offer_analysis"
    NEGOTIATION_COACHING = "negotiation_coaching"

    # --- Phase 4: Trust, Safety & Engagement ---
    SCAM_DETECTION = "scam_detection"
    WEEKLY_REVIEW = "weekly_review"

    # --- Phase 5: Career Operating System ---
    ONBOARDING_PLANNING = "onboarding_planning"
    CAREER_ANALYSIS = "career_analysis"
    MARKET_INTELLIGENCE = "market_intelligence"
    LEARNING_PATH = "learning_path"
    NARRATIVE_SYNTHESIS = "narrative_synthesis"
    CERTIFICATION_ROI = "certification_roi"
    SERVICE_EXIT_PLANNING = "service_exit_planning"


class ProviderName(StrEnum):
    """
    LLM provider identifiers.

    Each provider has a corresponding settings class in src/core/config.py
    (AnthropicSettings, OpenAISettings, GroqSettings) and a LangChain
    integration package (langchain-anthropic, langchain-openai, langchain-groq).
    """

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GROQ = "groq"


class CircuitState(StrEnum):
    """
    Circuit breaker states (standard three-state pattern).

    CLOSED: normal operation, requests flow through.
    OPEN: provider is unhealthy, requests are blocked to avoid timeouts.
    HALF_OPEN: recovery probe — one test request allowed to check if the
               provider has recovered. Success -> CLOSED, failure -> OPEN.
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModelConfig:
    """
    Configuration for a single model in the routing table.

    Each entry describes which provider and model to use, plus task-specific
    generation parameters. The routing table lists these in priority order:
    the first available config wins.

    Attributes:
        provider: Which LLM provider serves this model.
        model_name: Provider-specific model identifier (e.g., "claude-sonnet-4-5-20250929").
        max_tokens: Maximum tokens in the response. Sized per task — cover
            letters need more room than match scores.
        temperature: Sampling temperature. Creative tasks (cover letters)
            use higher values; extraction tasks use 0.0 for determinism.
    """

    provider: ProviderName
    model_name: str
    max_tokens: int
    temperature: float


# ---------------------------------------------------------------------------
# Routing table
# ---------------------------------------------------------------------------
# Each task type maps to a list of ModelConfigs in priority order.
# The ModelManager tries each config in sequence, skipping providers that
# are unavailable (missing API key or circuit breaker open).
#
# The routing decisions follow from the DETAILED_PLAN:
#   - Creative/analytical tasks -> Claude Sonnet (best reasoning + writing)
#   - Structured extraction -> GPT-4o-mini (good at JSON, cheap)
#   - Fast/cheap tasks -> Claude Haiku (low latency, low cost)
#   - Fallback for all -> Groq Llama (free tier, 500K tokens/day)

# Shorthand helpers to reduce repetition in the table.
_sonnet = "claude-sonnet-4-5-20250929"
_haiku = "claude-haiku-4-5-20251001"
_gpt4o_mini = "gpt-4o-mini"
_llama70b = "llama-3.3-70b-versatile"
_llama8b = "llama-3.1-8b-instant"

ROUTING_TABLE: dict[TaskType, list[ModelConfig]] = {
    # Creative writing — needs strong language generation.
    TaskType.COVER_LETTER: [
        ModelConfig(ProviderName.ANTHROPIC, _sonnet, max_tokens=2048, temperature=0.7),
        ModelConfig(ProviderName.GROQ, _llama70b, max_tokens=2048, temperature=0.7),
    ],
    # Rewriting resume sections to match a JD — faithful to source material.
    TaskType.RESUME_TAILORING: [
        ModelConfig(ProviderName.ANTHROPIC, _sonnet, max_tokens=4096, temperature=0.3),
        ModelConfig(ProviderName.GROQ, _llama70b, max_tokens=4096, temperature=0.3),
    ],
    # Scoring and ranking jobs against user profile — analytical.
    TaskType.JOB_MATCHING: [
        ModelConfig(ProviderName.ANTHROPIC, _sonnet, max_tokens=1024, temperature=0.1),
        ModelConfig(ProviderName.GROQ, _llama70b, max_tokens=1024, temperature=0.1),
    ],
    # Summarizing company culture, tech stack, news.
    TaskType.COMPANY_RESEARCH: [
        ModelConfig(ProviderName.ANTHROPIC, _sonnet, max_tokens=2048, temperature=0.3),
        ModelConfig(ProviderName.GROQ, _llama70b, max_tokens=2048, temperature=0.3),
    ],
    # Short conversational responses — speed matters more than depth.
    TaskType.QUICK_CHAT: [
        ModelConfig(ProviderName.ANTHROPIC, _haiku, max_tokens=512, temperature=0.7),
        ModelConfig(ProviderName.GROQ, _llama8b, max_tokens=512, temperature=0.7),
    ],
    # Extracting structured JSON from unstructured text — deterministic.
    TaskType.DATA_EXTRACTION: [
        ModelConfig(ProviderName.OPENAI, _gpt4o_mini, max_tokens=2048, temperature=0.0),
        ModelConfig(ProviderName.GROQ, _llama70b, max_tokens=2048, temperature=0.0),
    ],
    # Generating interview questions — mix of creative and analytical.
    TaskType.INTERVIEW_PREP: [
        ModelConfig(ProviderName.ANTHROPIC, _sonnet, max_tokens=2048, temperature=0.5),
        ModelConfig(ProviderName.GROQ, _llama70b, max_tokens=2048, temperature=0.5),
    ],
    # LinkedIn/email messages — personalized, concise.
    TaskType.OUTREACH_MESSAGE: [
        ModelConfig(ProviderName.ANTHROPIC, _sonnet, max_tokens=1024, temperature=0.7),
        ModelConfig(ProviderName.GROQ, _llama70b, max_tokens=1024, temperature=0.7),
    ],
    # Parsing resume PDF/DOCX into structured data — deterministic.
    TaskType.RESUME_PARSING: [
        ModelConfig(ProviderName.OPENAI, _gpt4o_mini, max_tokens=4096, temperature=0.0),
        ModelConfig(ProviderName.GROQ, _llama70b, max_tokens=4096, temperature=0.0),
    ],
    # Crafting STAR stories from work experience — structured creativity.
    TaskType.STAR_STORY: [
        ModelConfig(ProviderName.ANTHROPIC, _sonnet, max_tokens=1024, temperature=0.5),
        ModelConfig(ProviderName.GROQ, _llama70b, max_tokens=1024, temperature=0.5),
    ],
    # Simulating an interviewer — conversational and adaptive.
    TaskType.MOCK_INTERVIEW: [
        ModelConfig(ProviderName.ANTHROPIC, _sonnet, max_tokens=2048, temperature=0.7),
        ModelConfig(ProviderName.GROQ, _llama70b, max_tokens=2048, temperature=0.7),
    ],
    # Catch-all for tasks that don't fit a specific category.
    TaskType.GENERAL: [
        ModelConfig(ProviderName.ANTHROPIC, _haiku, max_tokens=1024, temperature=0.5),
        ModelConfig(ProviderName.GROQ, _llama8b, max_tokens=1024, temperature=0.5),
    ],
    # --- Phase 0: Locale & Market Context ---
    # Market-aware career advisory — creative + contextual.
    TaskType.LOCALE_ADVISORY: [
        ModelConfig(ProviderName.ANTHROPIC, _sonnet, max_tokens=1024, temperature=0.5),
        ModelConfig(ProviderName.GROQ, _llama70b, max_tokens=1024, temperature=0.5),
    ],
    # CTC decomposition, salary comparison narrative — deterministic.
    TaskType.COMPENSATION_ANALYSIS: [
        ModelConfig(ProviderName.OPENAI, _gpt4o_mini, max_tokens=2048, temperature=0.0),
        ModelConfig(ProviderName.GROQ, _llama70b, max_tokens=2048, temperature=0.0),
    ],
    # Market-specific resume formatting — structured, low creativity.
    TaskType.REGIONAL_RESUME: [
        ModelConfig(ProviderName.OPENAI, _gpt4o_mini, max_tokens=4096, temperature=0.2),
        ModelConfig(ProviderName.GROQ, _llama70b, max_tokens=4096, temperature=0.2),
    ],
    # Company verification, scam pattern analysis — deterministic.
    TaskType.SCAM_INTELLIGENCE: [
        ModelConfig(ProviderName.OPENAI, _gpt4o_mini, max_tokens=2048, temperature=0.0),
        ModelConfig(ProviderName.GROQ, _llama70b, max_tokens=2048, temperature=0.0),
    ],
    # Visa eligibility comparison — factual, low creativity.
    TaskType.VISA_NAVIGATION: [
        ModelConfig(ProviderName.ANTHROPIC, _sonnet, max_tokens=2048, temperature=0.3),
        ModelConfig(ProviderName.GROQ, _llama70b, max_tokens=2048, temperature=0.3),
    ],
    # Culture-calibrated interview prep — conversational.
    TaskType.CULTURAL_COACHING: [
        ModelConfig(ProviderName.ANTHROPIC, _sonnet, max_tokens=2048, temperature=0.6),
        ModelConfig(ProviderName.GROQ, _llama70b, max_tokens=2048, temperature=0.6),
    ],
    # --- Phase 1: Professional Identity ---
    # Guided achievement extraction — creative interview style.
    TaskType.ACHIEVEMENT_MINING: [
        ModelConfig(ProviderName.ANTHROPIC, _sonnet, max_tokens=2048, temperature=0.7),
        ModelConfig(ProviderName.GROQ, _llama70b, max_tokens=2048, temperature=0.7),
    ],
    # Deterministic skills mapping and proficiency assessment.
    TaskType.SKILLS_ANALYSIS: [
        ModelConfig(ProviderName.OPENAI, _gpt4o_mini, max_tokens=4096, temperature=0.0),
        ModelConfig(ProviderName.GROQ, _llama70b, max_tokens=4096, temperature=0.0),
    ],
    # --- Phase 2: Application Intelligence (4) ---
    # Creative application strategy — Claude Sonnet for nuanced decisions.
    TaskType.APPLICATION_ORCHESTRATION: [
        ModelConfig(ProviderName.ANTHROPIC, _sonnet, max_tokens=2048, temperature=0.5),
        ModelConfig(ProviderName.GROQ, _llama70b, max_tokens=2048, temperature=0.5),
    ],
    # Deterministic pattern analysis from application outcome data.
    TaskType.SUCCESS_PATTERN: [
        ModelConfig(ProviderName.OPENAI, _gpt4o_mini, max_tokens=2048, temperature=0.0),
        ModelConfig(ProviderName.GROQ, _llama70b, max_tokens=2048, temperature=0.0),
    ],
    # Adaptive interview coaching — nuanced feedback requires strong reasoning.
    TaskType.INTERVIEW_COACHING: [
        ModelConfig(ProviderName.ANTHROPIC, _sonnet, max_tokens=2048, temperature=0.6),
        ModelConfig(ProviderName.GROQ, _llama70b, max_tokens=2048, temperature=0.6),
    ],
    # Deterministic question prediction from JD + company signals.
    TaskType.QUESTION_PREDICTION: [
        ModelConfig(ProviderName.OPENAI, _gpt4o_mini, max_tokens=2048, temperature=0.0),
        ModelConfig(ProviderName.GROQ, _llama70b, max_tokens=2048, temperature=0.0),
    ],
    # --- Phase 3: Negotiation War Room ---
    # Structured offer parsing — deterministic JSON extraction.
    TaskType.OFFER_ANALYSIS: [
        ModelConfig(ProviderName.OPENAI, _gpt4o_mini, max_tokens=4096, temperature=0.0),
        ModelConfig(ProviderName.GROQ, _llama70b, max_tokens=4096, temperature=0.0),
    ],
    # Negotiation coaching — creative recruiter simulation, needs strong reasoning.
    TaskType.NEGOTIATION_COACHING: [
        ModelConfig(ProviderName.ANTHROPIC, _sonnet, max_tokens=2048, temperature=0.7),
        ModelConfig(ProviderName.GROQ, _llama70b, max_tokens=2048, temperature=0.7),
    ],
    # Phase 4: Trust & Safety — precise, deterministic scoring needs low temp.
    TaskType.SCAM_DETECTION: [
        ModelConfig(ProviderName.OPENAI, _gpt4o_mini, max_tokens=2048, temperature=0.0),
        ModelConfig(ProviderName.GROQ, _llama70b, max_tokens=2048, temperature=0.0),
    ],
    # Weekly strategy review — analytical + creative synthesis.
    TaskType.WEEKLY_REVIEW: [
        ModelConfig(ProviderName.ANTHROPIC, _sonnet, max_tokens=2048, temperature=0.7),
        ModelConfig(ProviderName.GROQ, _llama70b, max_tokens=2048, temperature=0.7),
    ],
    # --- Phase 5: Career Operating System ---
    # Onboarding plan generation — structured + creative.
    TaskType.ONBOARDING_PLANNING: [
        ModelConfig(ProviderName.ANTHROPIC, _sonnet, max_tokens=2048, temperature=0.5),
        ModelConfig(ProviderName.GROQ, _llama70b, max_tokens=2048, temperature=0.5),
    ],
    # Career health analysis — analytical, needs strong reasoning.
    TaskType.CAREER_ANALYSIS: [
        ModelConfig(ProviderName.ANTHROPIC, _sonnet, max_tokens=2048, temperature=0.3),
        ModelConfig(ProviderName.GROQ, _llama70b, max_tokens=2048, temperature=0.3),
    ],
    # Market intelligence — deterministic signal classification.
    TaskType.MARKET_INTELLIGENCE: [
        ModelConfig(ProviderName.OPENAI, _gpt4o_mini, max_tokens=2048, temperature=0.0),
        ModelConfig(ProviderName.GROQ, _llama70b, max_tokens=2048, temperature=0.0),
    ],
    # Learning path generation — structured + creative.
    TaskType.LEARNING_PATH: [
        ModelConfig(ProviderName.ANTHROPIC, _sonnet, max_tokens=2048, temperature=0.5),
        ModelConfig(ProviderName.GROQ, _llama70b, max_tokens=2048, temperature=0.5),
    ],
    # Career narrative synthesis — creative writing.
    TaskType.NARRATIVE_SYNTHESIS: [
        ModelConfig(ProviderName.ANTHROPIC, _sonnet, max_tokens=2048, temperature=0.7),
        ModelConfig(ProviderName.GROQ, _llama70b, max_tokens=2048, temperature=0.7),
    ],
    # Certification ROI ranking — analytical.
    TaskType.CERTIFICATION_ROI: [
        ModelConfig(ProviderName.OPENAI, _gpt4o_mini, max_tokens=2048, temperature=0.0),
        ModelConfig(ProviderName.GROQ, _llama70b, max_tokens=2048, temperature=0.0),
    ],
    # Service company exit planning — creative + strategic.
    TaskType.SERVICE_EXIT_PLANNING: [
        ModelConfig(ProviderName.ANTHROPIC, _sonnet, max_tokens=2048, temperature=0.5),
        ModelConfig(ProviderName.GROQ, _llama70b, max_tokens=2048, temperature=0.5),
    ],
}


# ---------------------------------------------------------------------------
# Cost table
# ---------------------------------------------------------------------------
# Maps model names to (input_cost, output_cost) per million tokens in USD.
#
# Groq models are priced at $0 because we use the free tier (500K tokens/day).
# If we exceed the free tier, Groq charges per-token — update these values then.
#
# Prices sourced from provider pricing pages (February 2026).
# The cost_tracker module uses these to pre-calculate cost_usd at write time.

COST_PER_MILLION_TOKENS: dict[str, tuple[float, float]] = {
    # Anthropic
    _sonnet: (3.00, 15.00),
    _haiku: (0.80, 4.00),
    # OpenAI
    _gpt4o_mini: (0.15, 0.60),
    # Groq (free tier — no charge within 500K tokens/day)
    _llama70b: (0.0, 0.0),
    _llama8b: (0.0, 0.0),
}
