"""An asset's price under parallel moves of its yield, from the modified duration of its profile (RN-25).

The rates scenario of the asset's «What if…?»: for each move asked — rates up or down by half a point, one point, two
points — the price changes by about −modified duration × Δy (``financial_math.bond_duration``). The duration is the
asset profile's ``modified_duration`` holding the analysis day (Borsa Italiana on a bond), handed in by the risk scope
with the day it was read and its source. The scenario exists where the profile holds one, whatever the asset's type;
without one the answer is unavailable and says why (``no_modified_duration``), never a zero. It reads no price, so no
observation gate applies (``results.available_observations``).
"""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, field_validator

from backend.app.schemas.risk.outputs import RiskRateShockOutput, RiskRateShockScenario
from backend.app.schemas.risk.vocabulary import RiskErrorCode, RiskMode, RiskOutputKind, RiskScopeKind
from backend.app.services.financial_math.bond_duration import duration_price_change
from backend.app.services.platform.provider_registry import register_plugin
from backend.app.services.risk.base import RiskAnalytic, RiskComputation, RiskExecutionContext, RiskUnavailableError
from backend.app.services.risk.registry import RiskAnalyticRegistry

#: The largest move asked, as a decimal ratio (two points, the page's largest step): past it a first-order figure says
#: little, and on a long bond it could fall below −100 %.
MAX_YIELD_CHANGE = 0.02


class RateShockParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    #: The parallel moves of the yield, as decimal ratios (0.01 == one point up, -0.01 one point down), in the order the
    #: page shows them. One to twelve, each different from zero and within two points, none twice.
    yield_changes: list[FiniteFloat] = Field(..., min_length=1, max_length=12)

    @field_validator("yield_changes")
    @classmethod
    def validate_moves(cls, value: list[float]) -> list[float]:
        if len(value) != len(set(value)):
            raise ValueError("rate shock yield changes must be unique")
        if any(change == 0 or not math.isfinite(change) or abs(change) > MAX_YIELD_CHANGE for change in value):
            raise ValueError("rate shock yield changes must be non-zero and within two points")
        return value


@register_plugin(RiskAnalyticRegistry)
class RateShockAnalytic(RiskAnalytic):
    analytic_code = "rate_shock"
    algorithm_version = "1.0.0"
    name_i18n_key = "risk.analytics.rateShock.name"
    description_i18n_key = "risk.analytics.rateShock.description"
    output_kind = RiskOutputKind.RATE_SHOCK
    supported_scopes = (RiskScopeKind.ASSET,)
    supported_modes = (RiskMode.CURRENT_COMPOSITION,)
    params_model = RateShockParams
    min_observations = 1

    def compute(self, params: RateShockParams, context: RiskExecutionContext) -> RiskComputation:
        scope_asset_ids = context.requested_scope_asset_ids or context.scope_asset_ids
        classification = context.asset_classifications.get(scope_asset_ids[0]) if scope_asset_ids else None
        duration = classification.modified_duration if classification is not None else None
        if classification is None or duration is None or classification.modified_duration_read_on is None or not classification.modified_duration_source:
            raise RiskUnavailableError(
                "The asset profile holds no modified duration",
                code=RiskErrorCode.DATA_UNAVAILABLE,
                details={"reason": "no_modified_duration"},
            )
        return RiskComputation(
            output=RiskRateShockOutput(
                modified_duration=duration,
                duration_read_on=classification.modified_duration_read_on,
                duration_source=classification.modified_duration_source,
                scenarios=[RiskRateShockScenario(yield_change=change, price_change=duration_price_change(duration, change)) for change in params.yield_changes],
            ),
            method="modified_duration_first_order",
        )
