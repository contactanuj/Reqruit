"""
Offer document model — structured compensation analysis for job offers.

Each offer is parsed from raw text (pasted offer letter or CTC breakdown)
into structured components with absolute values, percentages, and confidence
levels. Supports both US and India compensation structures.

Design decisions
----------------
Why OfferComponent as an embedded model (not a separate collection):
    Components are always accessed together with their parent offer.
    Embedding avoids joins and ensures atomic reads/writes. A typical
    offer has 5-15 components — well within MongoDB's 16MB document limit.

Why missing_fields and suggestions as top-level lists:
    When the LLM can't parse a field, it flags it. These lists surface
    gaps to the user so they can request missing info from the employer.
    Keeping them top-level makes them easy to display in the UI without
    iterating through all components.
"""

from datetime import datetime, timezone

from beanie import Indexed, PydanticObjectId
from pydantic import BaseModel
from pymongo import DESCENDING, IndexModel

from src.db.base_document import TimestampedDocument


class OfferComponent(BaseModel):
    """
    A single compensation line item in the offer breakdown.

    Fields:
        name: Component label (e.g., "Base Salary", "HRA", "ESOPs").
        value: Monetary value in the specified currency.
        currency: ISO currency code (default INR for India-first product).
        frequency: How often this is paid — annual, monthly, or one_time.
        is_guaranteed: Whether this component is guaranteed or variable.
        confidence: Parsing confidence — high, medium, or low.
        pct_of_total: Percentage of total annual compensation.
    """

    name: str
    value: float
    currency: str = "INR"
    frequency: str = "annual"
    is_guaranteed: bool = True
    confidence: str = "high"
    pct_of_total: float = 0.0


class NegotiationOutcome(BaseModel):
    """Embedded record of how a negotiation concluded."""

    initial_offer_total: float
    final_offer_total: float
    delta_absolute: float  # final - initial
    delta_percentage: float  # ((final - initial) / initial) * 100
    strategy_used: str
    outcome_notes: str = ""
    recorded_at: datetime = datetime.now(tz=timezone.utc)


class Offer(TimestampedDocument):
    """
    Structured compensation analysis for a job offer.

    Fields:
        user_id: Owner of this offer.
        application_id: Optional link to an Application document.
        company_name: Company making the offer.
        role_title: Job title in the offer.
        components: Parsed compensation components.
        total_comp_annual: Sum of all annual components.
        market_percentile: Where this offer sits in the market (0-100).
        negotiation_initial_offer: Pre-negotiation total.
        negotiation_final_offer: Post-negotiation total.
        negotiation_delta: Difference (final - initial).
        decision: User's decision (accepted, rejected, negotiating, etc.).
        notes: Free-text user notes.
        locale_market: Market code (e.g., "IN", "US").
        raw_text: Original offer text submitted for parsing.
        missing_fields: Fields the parser couldn't extract.
        suggestions: What to ask the employer for missing info.
    """

    user_id: Indexed(PydanticObjectId)
    application_id: PydanticObjectId | None = None
    company_name: str
    role_title: str
    components: list[OfferComponent] = []
    total_comp_annual: float = 0.0
    market_percentile: float | None = None
    negotiation_initial_offer: float | None = None
    negotiation_final_offer: float | None = None
    negotiation_delta: float | None = None
    decision: str = ""
    notes: str = ""
    locale_market: str = ""
    raw_text: str = ""
    missing_fields: list[str] = []
    suggestions: list[str] = []
    # Aggregation grouping fields (Story 12-1)
    role_family: str = ""
    company_stage: str = ""
    region: str = ""
    negotiation_outcome: NegotiationOutcome | None = None

    class Settings:
        name = "offers"
        indexes = [
            IndexModel(
                [("user_id", 1), ("created_at", DESCENDING)],
                name="user_created_idx",
            ),
        ]
