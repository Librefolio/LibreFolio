"""Deterministic hypothetical and historical-replay stress analytics."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.risk import (
    RiskErrorCode,
    RiskMode,
    RiskOutputKind,
    RiskReturnBasis,
    RiskScopeKind,
    RiskStressImpact,
    RiskStressMethod,
    RiskStressOutput,
)
from backend.app.services.provider_registry import RiskAnalyticRegistry, register_plugin
from backend.app.services.risk.analytic_helpers import (
    prepared_asset_return_points,
)
from backend.app.services.risk.base import (
    RiskAnalytic,
    RiskComputation,
    RiskUnavailableError,
)
from backend.app.services.risk.metrics import (
    compounded_return,
    current_buy_and_hold_returns,
    hypothetical_stress_return,
)


class StressParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: RiskStressMethod
    shocks: Dict[str, FiniteFloat] = Field(default_factory=dict)
    replay_range: Optional[DateRangeModel] = None

    @model_validator(mode="after")
    def validate_method_inputs(self) -> StressParams:
        if self.method == RiskStressMethod.HYPOTHETICAL:
            if not self.shocks:
                raise ValueError("hypothetical stress requires shocks")
            if self.replay_range is not None:
                raise ValueError("hypothetical stress cannot declare replay_range")
            if any(value < -1 for value in self.shocks.values()):
                raise ValueError("stress shocks must be greater than or equal to -1")
        else:
            if self.replay_range is None:
                raise ValueError("historical replay requires replay_range")
            if self.shocks:
                raise ValueError("historical replay cannot declare shocks")
        return self


def _amount(value: Optional[Decimal], return_value: float) -> Optional[Decimal]:
    if value is None:
        return None
    stable_return = Decimal(str(return_value)).quantize(Decimal("0.000000000001"))
    return value * stable_return


@register_plugin(RiskAnalyticRegistry)
class StressAnalytic(RiskAnalytic):
    analytic_code = "stress"
    algorithm_version = "1.0.0"
    name_i18n_key = "risk.analytics.stress.name"
    description_i18n_key = "risk.analytics.stress.description"
    output_kind = RiskOutputKind.STRESS
    supported_scopes = (
        RiskScopeKind.ASSET,
        RiskScopeKind.ASSET_SET,
        RiskScopeKind.PORTFOLIO,
        RiskScopeKind.BROKER,
    )
    supported_modes = (RiskMode.CURRENT_COMPOSITION,)
    params_model = StressParams
    min_observations = 1

    def compute(self, params, context):
        if params.method == RiskStressMethod.HYPOTHETICAL:
            return self._hypothetical(params, context)
        return self._historical(params, context)

    @staticmethod
    def _hypothetical(params, context):
        scope_asset_ids = context.requested_scope_asset_ids or context.scope_asset_ids
        try:
            parsed_shocks = {int(asset_id): float(value) for asset_id, value in params.shocks.items()}
        except ValueError as exc:
            raise RiskUnavailableError(
                "Stress shock keys must be asset IDs",
                code=RiskErrorCode.INVALID_PARAMETERS,
            ) from exc
        unknown = set(parsed_shocks) - set(scope_asset_ids)
        if unknown:
            raise RiskUnavailableError(
                "Stress shocks reference assets outside the selected scope",
                code=RiskErrorCode.INVALID_PARAMETERS,
                details={"asset_ids": sorted(unknown)},
            )
        shocks = {asset_id: parsed_shocks.get(asset_id, 0.0) for asset_id in scope_asset_ids}
        weighted_scope = context.scope_kind in {
            RiskScopeKind.PORTFOLIO,
            RiskScopeKind.BROKER,
        }
        portfolio_return: Optional[float] = None
        contributions: dict[int, float] = {}
        if weighted_scope:
            portfolio_return, contributions = hypothetical_stress_return(
                shocks,
                {asset_id: context.weights[asset_id] for asset_id in scope_asset_ids},
            )
        elif context.scope_kind == RiskScopeKind.ASSET:
            portfolio_return = shocks[scope_asset_ids[0]]

        impacts = [
            RiskStressImpact(
                asset_id=asset_id,
                weight=context.weights.get(asset_id) if weighted_scope else None,
                shock_return=shock,
                contribution_return=contributions.get(asset_id),
                impact_amount=_amount(context.asset_values.get(asset_id), shock),
            )
            for asset_id, shock in shocks.items()
        ]
        return RiskComputation(
            output=RiskStressOutput(
                method=RiskStressMethod.HYPOTHETICAL,
                portfolio_return=portfolio_return,
                impact_amount=_amount(context.scope_value, portfolio_return) if portfolio_return is not None else None,
                impacts=impacts,
            ),
            method="hypothetical_shock",
            n_observations=context.prepared_series.n_observations if context.prepared_series else context.n_observations,
            calendar_days=context.prepared_series.calendar_days if context.prepared_series else context.calendar_days,
            annualization_factor=context.prepared_series.annualization_factor if context.prepared_series else context.annualization_factor,
            coverage=context.prepared_series.calendar_coverage if context.prepared_series else context.coverage,
            return_basis=RiskReturnBasis.PRICE_ONLY,
        )

    @staticmethod
    def _historical(params, context):
        replay_end = params.replay_range.end or params.replay_range.start
        selected: dict[int, tuple[list[date], list[float]]] = {}
        replay_baseline: Optional[date] = None
        for asset_id in context.scope_asset_ids:
            points = prepared_asset_return_points(context, asset_id)
            pairs = [(point_date, previous_date, value) for point_date, previous_date, value in points if params.replay_range.start <= point_date <= replay_end]
            if not pairs:
                raise RiskUnavailableError(
                    "Historical replay has no observations in the requested range",
                    code=RiskErrorCode.INSUFFICIENT_HISTORY,
                    details={"asset_id": asset_id},
                )
            selected[asset_id] = (
                [point_date for point_date, _previous_date, _value in pairs],
                [value for _point_date, _previous_date, value in pairs],
            )
            replay_baseline = replay_baseline or pairs[0][1]

        asset_returns = {asset_id: compounded_return(values) for asset_id, (_dates, values) in selected.items()}
        weighted_scope = context.scope_kind in {
            RiskScopeKind.PORTFOLIO,
            RiskScopeKind.BROKER,
        }
        portfolio_return: Optional[float] = None
        if weighted_scope:
            portfolio_returns = current_buy_and_hold_returns(
                {asset_id: values for asset_id, (_dates, values) in selected.items()},
                {asset_id: context.weights[asset_id] for asset_id in context.scope_asset_ids},
                cash_weight=context.cash_weight,
            )
            portfolio_return = compounded_return(portfolio_returns)
        elif context.scope_kind == RiskScopeKind.ASSET:
            portfolio_return = asset_returns[context.scope_asset_ids[0]]

        selected_dates = next(iter(selected.values()))[0]
        calendar_days = (selected_dates[-1] - replay_baseline).days if replay_baseline is not None else 0
        n_observations = len(selected_dates)
        annualization_factor = n_observations * 365 / calendar_days if calendar_days > 0 else None
        return RiskComputation(
            output=RiskStressOutput(
                method=RiskStressMethod.HISTORICAL_REPLAY,
                portfolio_return=portfolio_return,
                impact_amount=_amount(context.scope_value, portfolio_return) if portfolio_return is not None else None,
                replay_range=params.replay_range,
                impacts=[
                    RiskStressImpact(
                        asset_id=asset_id,
                        weight=context.weights.get(asset_id) if weighted_scope else None,
                        shock_return=return_value,
                        contribution_return=context.weights.get(asset_id, 0.0) * return_value if weighted_scope else None,
                        impact_amount=_amount(context.asset_values.get(asset_id), return_value),
                    )
                    for asset_id, return_value in asset_returns.items()
                ],
            ),
            method="historical_replay_current_buy_and_hold",
            analyzed_range=DateRangeModel(start=selected_dates[0], end=selected_dates[-1]),
            n_observations=n_observations,
            calendar_days=calendar_days,
            annualization_factor=annualization_factor,
            coverage=1.0,
            return_basis=RiskReturnBasis.PRICE_ONLY,
        )
