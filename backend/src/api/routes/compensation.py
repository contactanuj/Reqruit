"""
Compensation routes: ESOP valuation, variable pay analysis, and more.

India-specific compensation intelligence. All endpoints require JWT auth.
"""

import json
from datetime import date, datetime

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel, field_validator, model_validator

from src.agents.compensation_coach import compensation_coach_agent
from src.api.dependencies import get_current_user, get_variable_pay_benchmark_repository
from src.db.documents.user import User
from src.repositories.variable_pay_benchmark_repository import VariablePayBenchmarkRepository
from src.services.buyout_calculator_service import BuyoutCalculatorService
from src.services.esop_valuation_service import ESOPValuationService
from src.services.variable_pay_risk_service import VariablePayRiskService

logger = structlog.get_logger()

router = APIRouter(prefix="/compensation", tags=["compensation"])


# ---------------------------------------------------------------------------
# Inline Pydantic schemas
# ---------------------------------------------------------------------------


class ESOPGrantInput(BaseModel):
    shares: int
    strike_price: float
    cliff_months: int = 12
    vesting_frequency: str = "monthly"  # monthly or quarterly
    vesting_total_months: int = 48
    current_company_valuation: float
    fmv_per_share: float | None = None
    grant_date: date | None = None
    tax_slab_rate: float = 0.3


class ExitScenarioResponse(BaseModel):
    scenario_name: str
    exit_multiplier: float
    exit_valuation: float
    price_per_share_at_exit: float
    pre_tax_value: float
    perquisite_tax: float
    capital_gains_tax: float
    capital_gains_type: str
    net_post_tax_value: float


class VestingTrancheResponse(BaseModel):
    tranche_number: int
    shares: int
    vesting_date: date
    cumulative_shares: int


class ESOPValuationResponse(BaseModel):
    scenarios: list[ExitScenarioResponse]
    vesting_timeline: list[VestingTrancheResponse]
    cliff_warning: str | None = None
    cliff_date: date | None = None
    total_shares: int
    strike_price: float
    current_fmv: float


# ---------------------------------------------------------------------------
# Buyout Calculator schemas
# ---------------------------------------------------------------------------


class BuyoutCalculateRequest(BaseModel):
    monthly_basic: float
    contractual_notice_days: int
    served_days: int = 0
    offer_joining_date: date
    joining_bonus: float | None = None
    notice_start_date: date | None = None

    @field_validator("contractual_notice_days")
    @classmethod
    def notice_days_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("contractual_notice_days must be > 0")
        return v

    @field_validator("served_days")
    @classmethod
    def served_not_exceeding(cls, v: int, info) -> int:
        notice = info.data.get("contractual_notice_days")
        if notice is not None and v > notice:
            raise ValueError("served_days cannot exceed contractual_notice_days")
        return v


class BuyoutCalculateResponse(BaseModel):
    remaining_days: int
    natural_end_date: date
    buyout_required: bool
    buyout_cost: float
    gap_days: int | None = None
    daily_rate: float
    joining_bonus: float | None = None
    net_out_of_pocket: float | None = None
    recommendation: str | None = None
    offer_joining_date: date


# ---------------------------------------------------------------------------
# Variable Pay Risk schemas
# ---------------------------------------------------------------------------


class VariablePayRiskRequest(BaseModel):
    company_name: str
    variable_pay_pct: float
    annual_ctc: float


class VariablePayRiskResponse(BaseModel):
    stated_variable_amount: float
    estimated_actual_payout_pct: float
    expected_actual_amount: float
    risk_level: str
    data_source: str
    data_points_count: int | None = None
    last_updated: datetime | None = None
    confidence: str
    high_variable_warning: str | None = None


# ---------------------------------------------------------------------------
# POST /compensation/esop-valuation
# ---------------------------------------------------------------------------


@router.post("/esop-valuation", response_model=ESOPValuationResponse)
async def esop_valuation(
    body: ESOPGrantInput,
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> ESOPValuationResponse:
    """Calculate ESOP valuation with 3 exit scenarios and Indian tax impact."""
    service = ESOPValuationService()
    result = service.valuate(
        shares=body.shares,
        strike_price=body.strike_price,
        current_company_valuation=body.current_company_valuation,
        cliff_months=body.cliff_months,
        vesting_frequency=body.vesting_frequency,
        vesting_total_months=body.vesting_total_months,
        fmv_per_share=body.fmv_per_share,
        grant_date=body.grant_date,
        tax_slab_rate=body.tax_slab_rate,
    )

    logger.info(
        "esop_valuation_completed",
        user_id=str(current_user.id),
        shares=body.shares,
        scenarios_count=len(result.scenarios),
    )

    return ESOPValuationResponse(
        scenarios=[
            ExitScenarioResponse(
                scenario_name=s.scenario_name,
                exit_multiplier=s.exit_multiplier,
                exit_valuation=s.exit_valuation,
                price_per_share_at_exit=s.price_per_share_at_exit,
                pre_tax_value=s.pre_tax_value,
                perquisite_tax=s.perquisite_tax,
                capital_gains_tax=s.capital_gains_tax,
                capital_gains_type=s.capital_gains_type,
                net_post_tax_value=s.net_post_tax_value,
            )
            for s in result.scenarios
        ],
        vesting_timeline=[
            VestingTrancheResponse(
                tranche_number=t.tranche_number,
                shares=t.shares,
                vesting_date=t.vesting_date,
                cumulative_shares=t.cumulative_shares,
            )
            for t in result.vesting_timeline
        ],
        cliff_warning=result.cliff_warning,
        cliff_date=result.cliff_date,
        total_shares=result.total_shares,
        strike_price=result.strike_price,
        current_fmv=result.current_fmv,
    )


# ---------------------------------------------------------------------------
# POST /compensation/variable-pay-risk
# ---------------------------------------------------------------------------


@router.post("/variable-pay-risk", response_model=VariablePayRiskResponse)
async def variable_pay_risk(
    body: VariablePayRiskRequest,
    current_user: User = Depends(get_current_user),  # noqa: B008
    benchmark_repo: VariablePayBenchmarkRepository = Depends(get_variable_pay_benchmark_repository),  # noqa: B008, E501
) -> VariablePayRiskResponse:
    """Analyze variable pay risk using benchmark data."""
    service = VariablePayRiskService(benchmark_repo)
    result = await service.analyze(
        company_name=body.company_name,
        variable_pay_pct=body.variable_pay_pct,
        annual_ctc=body.annual_ctc,
    )

    logger.info(
        "variable_pay_risk_completed",
        user_id=str(current_user.id),
        company=body.company_name,
        risk_level=result.risk_level,
        data_source=result.data_source,
    )

    return VariablePayRiskResponse(
        stated_variable_amount=result.stated_variable_amount,
        estimated_actual_payout_pct=result.estimated_actual_payout_pct,
        expected_actual_amount=result.expected_actual_amount,
        risk_level=result.risk_level,
        data_source=result.data_source,
        data_points_count=result.data_points_count,
        last_updated=result.last_updated,
        confidence=result.confidence,
        high_variable_warning=result.high_variable_warning,
    )


# ---------------------------------------------------------------------------
# POST /compensation/buyout-calculate
# ---------------------------------------------------------------------------


@router.post("/buyout-calculate", response_model=BuyoutCalculateResponse)
async def buyout_calculate(
    body: BuyoutCalculateRequest,
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> BuyoutCalculateResponse:
    """Calculate notice period buyout cost and joining bonus offset."""
    service = BuyoutCalculatorService()
    result = service.calculate(
        monthly_basic=body.monthly_basic,
        contractual_notice_days=body.contractual_notice_days,
        served_days=body.served_days,
        offer_joining_date=body.offer_joining_date,
        joining_bonus=body.joining_bonus,
        notice_start_date=body.notice_start_date,
    )

    logger.info(
        "buyout_calculation_completed",
        user_id=str(current_user.id),
        buyout_required=result.buyout_required,
        remaining_days=result.remaining_days,
    )

    return BuyoutCalculateResponse(
        remaining_days=result.remaining_days,
        natural_end_date=result.natural_end_date,
        buyout_required=result.buyout_required,
        buyout_cost=result.buyout_cost,
        gap_days=result.gap_days,
        daily_rate=result.daily_rate,
        joining_bonus=result.joining_bonus,
        net_out_of_pocket=result.net_out_of_pocket,
        recommendation=result.recommendation,
        offer_joining_date=result.offer_joining_date,
    )


# ---------------------------------------------------------------------------
# Salary Coach schemas
# ---------------------------------------------------------------------------


class SalaryCoachRequest(BaseModel):
    current_ctc: float | None = None  # India
    current_salary: float | None = None  # US
    target_range_min: float
    target_range_max: float
    role_title: str
    company_name: str
    city: str = ""
    locale: str = "IN"  # IN or US
    company_context: str = ""

    @model_validator(mode="after")
    def at_least_one_comp(self):
        if self.current_ctc is None and self.current_salary is None:
            raise ValueError("At least one of current_ctc or current_salary must be provided")
        return self


class AnchoringScript(BaseModel):
    script_text: str
    strategy_name: str
    strategy_explanation: str
    risk_level: str


class SalaryCoachResponse(BaseModel):
    scripts: list[AnchoringScript]
    locale_used: str
    general_tips: list[str]


# ---------------------------------------------------------------------------
# POST /compensation/salary-coach
# ---------------------------------------------------------------------------


@router.post("/salary-coach", response_model=SalaryCoachResponse)
async def salary_coach(
    body: SalaryCoachRequest,
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> SalaryCoachResponse:
    """Generate salary anchoring scripts via the compensation coach agent."""
    state = {
        "locale": body.locale,
        "current_ctc": body.current_ctc,
        "current_salary": body.current_salary,
        "target_range_min": body.target_range_min,
        "target_range_max": body.target_range_max,
        "role_title": body.role_title,
        "company_name": body.company_name,
        "city": body.city,
        "company_context": body.company_context,
    }
    config = {"configurable": {"user_id": str(current_user.id)}}

    result = await compensation_coach_agent(state, config)

    scripts_raw = json.loads(result.get("scripts", "[]"))
    tips_raw = json.loads(result.get("general_tips", "[]"))

    scripts = [
        AnchoringScript(
            script_text=s.get("script_text", ""),
            strategy_name=s.get("strategy_name", "general"),
            strategy_explanation=s.get("strategy_explanation", ""),
            risk_level=s.get("risk_level", "medium"),
        )
        for s in scripts_raw
    ]

    logger.info(
        "salary_coach_completed",
        user_id=str(current_user.id),
        locale=body.locale,
        scripts_count=len(scripts),
    )

    return SalaryCoachResponse(
        scripts=scripts,
        locale_used=body.locale,
        general_tips=tips_raw,
    )
