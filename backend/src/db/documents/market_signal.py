"""
MarketSignal document — real-time market intelligence signals.

Stores market signals such as hiring trends, layoff alerts, skill demand
shifts, compensation changes, and industry disruption indicators.
"""

from datetime import datetime

from beanie import Indexed, PydanticObjectId
from pydantic import Field

from src.db.base_document import TimestampedDocument


class MarketSignal(TimestampedDocument):
    """
    A market intelligence signal relevant to a user's career context.

    Signals are classified by type (hiring_trend, layoff_alert, skill_demand,
    compensation_shift, disruption) and severity (info, warning, critical).
    """

    user_id: Indexed(PydanticObjectId) | None = None  # None = global signal
    signal_type: str  # hiring_trend, layoff_alert, skill_demand, compensation_shift, disruption
    severity: str = "info"  # info, warning, critical
    title: str = ""
    description: str = ""
    industry: str = ""
    region: str = ""
    source: str = ""  # where the signal originated
    confidence: float = 0.0  # 0.0-1.0
    tags: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None
    metadata: dict = Field(default_factory=dict)

    class Settings:
        name = "market_signals"
