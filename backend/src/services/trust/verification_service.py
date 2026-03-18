"""
TrustVerificationService — orchestrates trust score computation with caching.

Calls ScamDetectorAgent for LLM-powered analysis and applies email domain
matching as a rule-based overlay. Results are cached in-memory with a 1-hour TTL.
Also provides posting freshness analysis and JD red flag orchestration.
"""

import time
from datetime import datetime, timezone

import structlog

from src.agents.scam_detector import scam_detector_agent
from src.guardrails.jd_red_flag_analyzer import JDRedFlagAnalyzer
from src.services.trust.models import FreshnessScore, RedFlag, RiskCategory, RiskSignal, TrustScore

logger = structlog.get_logger()

# Personal email domains that flag a mismatch
_PERSONAL_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "aol.com", "protonmail.com", "mail.com", "yandex.com",
    "rediffmail.com", "live.com",
}

_CACHE_TTL_SECONDS = 3600  # 1 hour


class TrustVerificationService:
    """Orchestrates trust verification with in-memory TTL cache."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[TrustScore, float]] = {}

    async def verify(
        self,
        company_name: str,
        company_registration_number: str | None = None,
        recruiter_email: str | None = None,
        recruiter_linkedin_url: str | None = None,
        job_url: str | None = None,
    ) -> TrustScore:
        entity_id = self._build_entity_id(company_name, recruiter_email)

        cached = self._get_cached_score(entity_id)
        if cached is not None:
            logger.debug("trust_cache_hit", entity_id=entity_id)
            return cached

        # Build agent state
        state = {
            "company_name": company_name,
            "company_registration_number": company_registration_number,
            "recruiter_email": recruiter_email,
            "recruiter_linkedin_url": recruiter_linkedin_url,
            "job_url": job_url,
        }

        # Call LLM agent
        result = await scam_detector_agent(state)

        # Build risk signals from agent output
        risk_signals = [
            RiskSignal(
                signal_type=s.get("signal_type", "unknown"),
                description=s.get("description", ""),
                severity=s.get("severity", "medium"),
            )
            for s in result.get("risk_signals", [])
        ]

        # Rule-based overlay: email domain check
        email_signal = self._check_email_domain_match(recruiter_email, company_name)
        if email_signal is not None:
            risk_signals.append(email_signal)

        trust_score = TrustScore(
            company_verification_score=result.get("company_verification_score", 0.0),
            recruiter_verification_score=result.get("recruiter_verification_score", 0.0),
            posting_freshness_score=result.get("posting_freshness_score", 0.0),
            red_flag_count=result.get("red_flag_count", 0) + (1 if email_signal else 0),
            overall_trust_score=result.get("overall_trust_score", 50.0),
            risk_category=result.get("risk_category", RiskCategory.UNCERTAIN),
            risk_signals=risk_signals,
        )

        self._cache_score(entity_id, trust_score)
        logger.info(
            "trust_verification_complete",
            entity_id=entity_id,
            overall_score=trust_score.overall_trust_score,
            risk_category=trust_score.risk_category,
        )

        return trust_score

    def get_cached_score_for_job(self, job_id: str) -> TrustScore | None:
        """Lookup cached trust score by job_id key."""
        return self._get_cached_score(f"job:{job_id}")

    def cache_score_for_job(self, job_id: str, score: TrustScore) -> None:
        """Cache a trust score under a job_id key."""
        self._cache_score(f"job:{job_id}", score)

    @staticmethod
    def _check_email_domain_match(
        recruiter_email: str | None, company_name: str
    ) -> RiskSignal | None:
        if not recruiter_email or "@" not in recruiter_email:
            return None

        domain = recruiter_email.split("@", 1)[1].lower()

        if domain in _PERSONAL_EMAIL_DOMAINS:
            return RiskSignal(
                signal_type="PERSONAL_EMAIL_DOMAIN",
                description=f"Recruiter uses personal email domain ({domain}) instead of company email",
                severity="high",
            )

        # Simple heuristic: check if company name words appear in domain
        company_words = {w.lower() for w in company_name.split() if len(w) > 2}
        domain_base = domain.split(".")[0]
        if company_words and not any(w in domain_base for w in company_words):
            return RiskSignal(
                signal_type="EMAIL_DOMAIN_MISMATCH",
                description=f"Email domain ({domain}) does not match company name ({company_name})",
                severity="medium",
            )

        return None

    def _get_cached_score(self, entity_id: str) -> TrustScore | None:
        entry = self._cache.get(entity_id)
        if entry is None:
            return None
        score, timestamp = entry
        if time.monotonic() - timestamp > _CACHE_TTL_SECONDS:
            del self._cache[entity_id]
            return None
        return score

    def _cache_score(self, entity_id: str, score: TrustScore) -> None:
        self._cache[entity_id] = (score, time.monotonic())

    async def analyze_posting(
        self,
        job_title: str,
        company_name: str,
        jd_text: str,
        posted_date: str | None = None,
        salary_range: str | None = None,
        communication_channel: str | None = None,
        locale: str = "US",
    ) -> dict:
        """Orchestrate full posting analysis: freshness + red flags + LLM."""
        freshness = self.analyze_posting_freshness(posted_date)

        analyzer = JDRedFlagAnalyzer()
        red_flags = analyzer.analyze(jd_text, locale=locale)

        # Separate India-specific flags
        india_categories = {"PLACEMENT_FEE_ILLEGAL", "WHATSAPP_ONLY"}
        india_flags = [f for f in red_flags if f.category in india_categories]
        universal_flags = [f for f in red_flags if f.category not in india_categories]

        # Determine overall risk level
        high_count = sum(1 for f in red_flags if f.severity == "HIGH_RISK")
        medium_count = sum(1 for f in red_flags if f.severity == "MEDIUM_RISK")

        if high_count >= 2 or (high_count >= 1 and medium_count >= 2):
            overall_risk = "CRITICAL"
        elif high_count >= 1:
            overall_risk = "HIGH"
        elif medium_count >= 2:
            overall_risk = "MEDIUM"
        elif medium_count >= 1 or freshness.staleness_flag:
            overall_risk = "LOW"
        else:
            overall_risk = "NONE"

        # Generate recommended actions
        actions = self._generate_recommended_actions(red_flags, freshness, locale)

        return {
            "freshness": freshness,
            "red_flags": universal_flags,
            "india_specific_flags": india_flags,
            "recommended_actions": actions,
            "overall_risk_level": overall_risk,
        }

    @staticmethod
    def analyze_posting_freshness(posted_date: str | None) -> FreshnessScore:
        """Compute freshness score from posting date."""
        if not posted_date:
            return FreshnessScore(score=50.0, days_since_posted=0, staleness_flag=False)

        try:
            posted_dt = datetime.fromisoformat(posted_date.replace("Z", "+00:00"))
            now = datetime.now(tz=timezone.utc)
            days = max(0, (now - posted_dt).days)
        except (ValueError, TypeError):
            return FreshnessScore(score=50.0, days_since_posted=0, staleness_flag=False)

        score = max(0.0, min(100.0, 100.0 - (days * 2)))
        staleness = days > 30

        return FreshnessScore(
            score=score,
            days_since_posted=days,
            staleness_flag=staleness,
        )

    @staticmethod
    def _generate_recommended_actions(
        flags: list[RedFlag], freshness: FreshnessScore, locale: str
    ) -> list[str]:
        actions: list[str] = []
        categories = {f.category for f in flags}

        if "UPFRONT_FEE" in categories:
            actions.append("Do not pay any fee — legitimate employers never charge candidates")
        if "PLACEMENT_FEE_ILLEGAL" in categories:
            actions.append("Report to local labour commissioner — placement agency fees are illegal under Indian law")
        if "TELEGRAM_ONLY" in categories or "WHATSAPP_ONLY" in categories:
            actions.append("Request official company email communication before proceeding")
        if "VAGUE_WFH" in categories:
            actions.append("Verify the company exists and has a legitimate web presence")
        if "ABOVE_MARKET_SALARY" in categories:
            actions.append("Cross-check salary claims against market data on Glassdoor or Levels.fyi")
        if freshness.staleness_flag:
            actions.append("This posting may be stale (>30 days old) — verify the position is still open")
        if locale.upper() == "IN" and not actions:
            actions.append("Verify company on MCA portal (mca.gov.in) using CIN/LLPIN")

        if not actions:
            actions.append("Standard due diligence recommended — no significant red flags detected")

        return actions

    @staticmethod
    def _build_entity_id(company_name: str, recruiter_email: str | None) -> str:
        key = company_name.lower().strip()
        if recruiter_email:
            key += f":{recruiter_email.lower().strip()}"
        return key
