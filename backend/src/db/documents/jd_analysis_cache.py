"""
JDAnalysisCache document — shared cache for job description analysis.

Stores LLM-decoded JD analysis keyed by SHA-256 fingerprint of the normalized
job description text. Shared across users — same JD = single LLM decode.

TTL index on expires_at auto-removes entries after 30 days.
"""

from datetime import datetime

from pydantic import Field
from pymongo import ASCENDING, IndexModel

from src.db.base_document import TimestampedDocument


class JDAnalysisCache(TimestampedDocument):
    """
    Cached job description analysis.

    Fields:
        fingerprint: SHA-256 hash of normalized JD text (unique).
        analysis: LLM-decoded analysis result (structured dict).
        hit_count: Number of cache hits (for cost analytics).
        expires_at: TTL expiration date (30 days from creation).
        token_count: Tokens used for the original LLM decode.
        cost_usd: Cost of the original LLM decode.
    """

    fingerprint: str  # SHA-256 hex digest
    analysis: dict = Field(default_factory=dict)
    hit_count: int = 0
    expires_at: datetime | None = None
    token_count: int = 0
    cost_usd: float = 0.0

    class Settings:
        name = "jd_analysis_cache"
        indexes = [
            IndexModel(
                [(("fingerprint", ASCENDING))],
                unique=True,
            ),
            IndexModel(
                [(("expires_at", ASCENDING))],
                expireAfterSeconds=0,  # MongoDB removes when expires_at is reached
            ),
        ]
