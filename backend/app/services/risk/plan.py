"""The plan of one analytic in a risk request, and the kind of calculation it asks for."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel

from backend.app.schemas.risk.scope import RiskAnalyticRequest
from backend.app.schemas.risk.vocabulary import RiskReturnBasis, RiskStressMethod
from backend.app.services.risk.base import (
    RiskAnalytic,
    RiskExecutionContext,
    RiskSeriesInputs,
)


@dataclass(frozen=True, slots=True)
class AnalyticPlan:
    request: RiskAnalyticRequest
    analytic_class: type[RiskAnalytic]
    analytic: RiskAnalytic
    params: BaseModel


def is_historical_replay_plan(plan: AnalyticPlan) -> bool:
    return plan.request.analytic_code == "stress" and getattr(plan.params, "method", None) == RiskStressMethod.HISTORICAL_REPLAY


def is_simulation_plan(plan: AnalyticPlan) -> bool:
    """The simulation prepares its own history (RN-16, developer's Q4 c): all the common history, never the period."""
    return plan.request.analytic_code == "simulation"


def is_hypothetical_plan(plan: AnalyticPlan) -> bool:
    return plan.request.analytic_code == "stress" and getattr(plan.params, "method", None) == RiskStressMethod.HYPOTHETICAL


def reads_no_price_series(plan: AnalyticPlan) -> bool:
    """Whether the plan's figures come from no price series: the hypothetical stress (shocks on today's weights) and the
    rates scenario (the profile's duration, RN-25). The series' data quality, history warnings and exclusions are not
    theirs."""
    return is_hypothetical_plan(plan) or plan.request.analytic_code == "rate_shock"


def reads_asset_profile(plan: AnalyticPlan) -> bool:
    """Whether the plan reads the assets' profile: the hypothetical stress (countries and sectors, D3) and the rates
    scenario (the modified duration, RN-25)."""
    return is_hypothetical_plan(plan) or plan.request.analytic_code == "rate_shock"


def is_geography_hypothetical_plan(plan: AnalyticPlan) -> bool:
    return is_hypothetical_plan(plan) and getattr(getattr(plan, "params", None), "dimension", None).value == "geography"


def reads_the_twrr_alone(plan: AnalyticPlan, context: RiskExecutionContext) -> bool:
    """Whether the analytic reads the portfolio TWRR and no scope asset series (developer's decision of 29/09/2026).

    The TWRR already values every holding, so such a result loses nothing when a scope asset has no
    series of its own, and does not inherit the scope's exclusions.
    """
    return context.primary_return_basis == RiskReturnBasis.TWRR and plan.analytic_class.series_inputs != RiskSeriesInputs.SCOPE_ASSETS
