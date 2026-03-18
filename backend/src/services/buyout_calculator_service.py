"""
Notice period buyout calculator — deterministic calculator (no LLM).

Computes buyout cost, gap days, joining bonus offset, and negotiation
recommendations for notice period buyout scenarios.
"""

from datetime import date, timedelta


class BuyoutCalculateResult:
    """Result of a buyout cost calculation."""

    def __init__(
        self,
        remaining_days: int,
        natural_end_date: date,
        buyout_required: bool,
        buyout_cost: float,
        gap_days: int | None,
        daily_rate: float,
        joining_bonus: float | None,
        net_out_of_pocket: float | None,
        recommendation: str | None,
        offer_joining_date: date,
    ) -> None:
        self.remaining_days = remaining_days
        self.natural_end_date = natural_end_date
        self.buyout_required = buyout_required
        self.buyout_cost = buyout_cost
        self.gap_days = gap_days
        self.daily_rate = daily_rate
        self.joining_bonus = joining_bonus
        self.net_out_of_pocket = net_out_of_pocket
        self.recommendation = recommendation
        self.offer_joining_date = offer_joining_date


class BuyoutCalculatorService:
    """Deterministic notice period buyout cost calculator."""

    def calculate(
        self,
        monthly_basic: float,
        contractual_notice_days: int,
        served_days: int,
        offer_joining_date: date,
        joining_bonus: float | None = None,
        notice_start_date: date | None = None,
    ) -> BuyoutCalculateResult:
        """Calculate buyout cost and joining bonus offset."""
        remaining_days = contractual_notice_days - served_days
        daily_rate = monthly_basic / 30

        base_date = notice_start_date or date.today()
        natural_end_date = base_date + timedelta(days=remaining_days)

        buyout_required = offer_joining_date < natural_end_date
        buyout_cost = round(daily_rate * remaining_days, 2)
        gap_days = (natural_end_date - offer_joining_date).days if buyout_required else None

        net_out_of_pocket = None
        recommendation = None
        if joining_bonus is not None:
            net_out_of_pocket = round(buyout_cost - joining_bonus, 2)
            if net_out_of_pocket <= 0:
                recommendation = "Your joining bonus fully covers the buyout cost"
            elif net_out_of_pocket < buyout_cost * 0.5:
                recommendation = "Consider negotiating partial buyout reimbursement into your offer"
            else:
                recommendation = (
                    "Strongly recommend negotiating buyout reimbursement "
                    "— significant out-of-pocket cost"
                )

        return BuyoutCalculateResult(
            remaining_days=remaining_days,
            natural_end_date=natural_end_date,
            buyout_required=buyout_required,
            buyout_cost=buyout_cost,
            gap_days=gap_days,
            daily_rate=round(daily_rate, 2),
            joining_bonus=joining_bonus,
            net_out_of_pocket=net_out_of_pocket,
            recommendation=recommendation,
            offer_joining_date=offer_joining_date,
        )
