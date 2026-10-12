"""Per-asset relative performance against one shared comparison asset."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.risk import (
    RiskAssetSetComparisonItem,
    RiskAssetSetComparisonOutput,
    RiskErrorCode,
    RiskFreeReference,
    RiskMode,
    RiskOutputKind,
    RiskScopeKind,
    RiskWarning,
)
from backend.app.services.data_quality_thresholds import RISK_MIN_OBSERVATIONS
from backend.app.services.provider_registry import RiskAnalyticRegistry, register_plugin
from backend.app.services.risk.analytic_helpers import (
    prepared_asset_returns,
    prepared_scope_series,
    require_annualization_factor,
)
from backend.app.services.risk.base import (
    RiskAnalytic,
    RiskComputation,
    RiskExecutionContext,
    RiskUnavailableError,
)
from backend.app.services.risk.metrics import (
    annualized_expected_return,
    annualized_sharpe,
    annualized_sortino,
    annualized_volatility,
    comparison_summary,
)


class AssetSetComparisonParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    comparison_asset_id: int = Field(
        ge=1,
        json_schema_extra={
            "x-control": "comparison_asset",
            "x-i18n-key": "chartSettings.params.comparisonAsset",
            "x-control-order": 1,
        },
    )
    risk_free_annual_rate: float = Field(
        0.0,
        gt=-1,
        json_schema_extra={
            "x-i18n-key": "chartSettings.params.riskFreeAnnualRate",
            "x-control-order": 2,
            "x-step": 0.001,
        },
    )
    target_annual_return: float = Field(
        0.0,
        gt=-1,
        json_schema_extra={
            "x-i18n-key": "risk.params.targetAnnualReturn",
            "x-control-order": 3,
            "x-step": 0.001,
        },
    )


@register_plugin(RiskAnalyticRegistry)
class AssetSetComparisonAnalytic(RiskAnalytic):
    """One beta per selected asset against a single reference.

    WHY THIS IS A CODE OF ITS OWN AND NOT A COLUMN ON ``asset_set_risk_return``.
    ``comparison_asset_id`` is required and has no default: there is no sensible
    benchmark to fall back to, which is why the singular analytic demands one
    too. Folding beta into the risk/return payload would have forced one of two
    outcomes — either a benchmark becomes mandatory in order to draw a scatter,
    which it is not, or the parameter becomes optional. An optional parameter is
    the same mechanism this family was created to avoid one level up: the moment
    a required input can be omitted, the payload has to describe what it did
    without it, and "what it did without it" is where invented values live.

    Two codes in one request cost one preparation, because the service prepares
    the series once per request and not once per analytic. So the separation is
    free in exactly the dimension that matters.

    ⚠️ THE REFERENCE IS PREPARED WITH THE SUBJECTS, NOT BESIDE THEM. The service
    adds every analytic's comparison asset to the same bulk price load, so the
    reference lands on the same joint calendar as the selection. Its own
    volatility and expected return are published here for the same reason the
    singular analytic publishes them: a benchmark drawn from a different window
    than the dots would sit somewhere no measurement puts it. It also means the
    reference participates in the calendar intersection — adding a thinly traded
    benchmark can shorten the window for everyone, which is correct and visible
    in ``n_observations``.

    📌 AN UNDEFINED BETA IS REPORTED AS UNDEFINED. Beta divides by the
    reference's variance and correlation divides by both, so a flat series makes
    them undefined rather than zero — and zero would read as "measured, and they
    are unrelated", which is a different and much stronger claim.

    🎯 THE REFERENCE MAY ALSO BE SELECTED, AND IS STILL NEVER A SUBJECT (D371).
    Five selected ETFs compared against the core one, which is among them: the
    selection keeps it, and its own volatility and return are measured like the
    others', but it is the yardstick here, so it is left out of ``items``. Its beta
    and correlation with itself would be 1 by construction — a tautology, not a
    measurement — and the output model still refuses them. The window does not
    move: the reference was already prepared with the selection.
    """

    analytic_code = "asset_set_comparison"
    # 1.2.0 — the payload adds the reference's own Sharpe and Sortino, charged the rate and the
    # target the request gives (both 0 by default). The other numbers are unchanged.
    algorithm_version = "1.2.0"
    name_i18n_key = "risk.analytics.assetSetComparison.name"
    description_i18n_key = "risk.analytics.assetSetComparison.description"
    output_kind = RiskOutputKind.COMPARISON_SET
    supported_scopes = (RiskScopeKind.ASSET_SET,)
    supported_modes = (RiskMode.HISTORICAL,)
    params_model = AssetSetComparisonParams
    min_observations = RISK_MIN_OBSERVATIONS

    def compute(self, params: AssetSetComparisonParams, context: RiskExecutionContext) -> RiskComputation:
        series = prepared_scope_series(context)
        _reference_dates, reference_returns = prepared_asset_returns(context, params.comparison_asset_id)
        prepared = context.prepared_series
        observations = prepared.n_observations if prepared else 0
        # ⚠️ UNREACHABLE THROUGH THE SERVICE, AND DELIBERATELY KEPT — do not
        # "harmonise" it away with the one in asset_set_var, which is a different
        # animal. `_available_observations` hands the service this very number
        # and compares it against this very minimum before compute() is called,
        # so the service refuses first. The var analytic's check survives because
        # it tests the *compounded* count, which the service cannot know. This
        # one is the contract stated where a direct caller can also see it.
        if observations < self.min_observations:
            raise RiskUnavailableError(
                "Comparison has insufficient common observations",
                code=RiskErrorCode.INSUFFICIENT_HISTORY,
                details={"observations": observations, "required": self.min_observations},
            )

        # One factor for the whole payload, because one joint calendar produces
        # one factor. Deriving it per asset would have implied they could differ.
        annualization = require_annualization_factor(context)
        undefined_beta: list[int] = []
        undefined_correlation: list[int] = []
        items: list[RiskAssetSetComparisonItem] = []

        for asset_id, _dates, returns in series:
            # The reference may also be selected (D371): it is the yardstick of the others,
            # not a subject, so it is skipped rather than measured against itself.
            if asset_id == params.comparison_asset_id:
                continue
            summary = comparison_summary(returns, reference_returns, annualization)
            if summary.beta is None:
                undefined_beta.append(asset_id)
            if summary.correlation is None:
                undefined_correlation.append(asset_id)
            items.append(
                RiskAssetSetComparisonItem(
                    asset_id=asset_id,
                    active_return=summary.active_return,
                    tracking_error=summary.tracking_error,
                    information_ratio=summary.information_ratio,
                    correlation=summary.correlation,
                    beta=summary.beta,
                )
            )

        comparison_sharpe = annualized_sharpe(reference_returns, annualization, annual_risk_free_rate=params.risk_free_annual_rate)
        comparison_sortino = annualized_sortino(reference_returns, annualization, annual_target_return=params.target_annual_return)

        warnings: list[RiskWarning] = []
        if comparison_sharpe is None:
            warnings.append(
                RiskWarning(
                    code="sharpe_undefined",
                    message_i18n_key="risk.warnings.sharpe_undefined_assets",
                    message="Sharpe is undefined for the comparison asset because its volatility is zero.",
                    details={"asset_ids": [params.comparison_asset_id]},
                )
            )
        if comparison_sortino is None:
            warnings.append(
                RiskWarning(
                    code="sortino_undefined",
                    message_i18n_key="risk.warnings.sortino_undefined_assets",
                    message="Sortino is undefined for the comparison asset because its downside deviation is zero.",
                    details={"asset_ids": [params.comparison_asset_id]},
                )
            )
        if undefined_beta:
            warnings.append(
                RiskWarning(
                    code="comparison_beta_undefined",
                    message_i18n_key="risk.warnings.comparison_beta_undefined_assets",
                    message="Beta is undefined for one or more assets because the comparison asset has zero variance.",
                    details={"asset_ids": undefined_beta},
                )
            )
        if undefined_correlation:
            warnings.append(
                RiskWarning(
                    code="comparison_correlation_undefined",
                    message_i18n_key="risk.warnings.comparison_correlation_undefined_assets",
                    message="Correlation is undefined for one or more assets because at least one series has zero variance.",
                    details={"asset_ids": undefined_correlation},
                )
            )

        return RiskComputation(
            output=RiskAssetSetComparisonOutput(
                comparison_asset_id=params.comparison_asset_id,
                observations=observations,
                comparison_volatility=annualized_volatility(reference_returns, annualization),
                comparison_expected_annual_return=annualized_expected_return(reference_returns, annualization),
                comparison_sharpe=comparison_sharpe,
                comparison_sortino=comparison_sortino,
                items=items,
            ),
            method="comparison_asset",
            warnings=tuple(warnings),
            risk_free=RiskFreeReference(
                annual_rate=params.risk_free_annual_rate,
                source="analytic_param",
                currency=context.target_currency,
            ),
            comparison_asset_id=params.comparison_asset_id,
            n_observations=observations,
            calendar_days=prepared.calendar_days if prepared else 0,
            annualization_factor=annualization,
            coverage=prepared.calendar_coverage if prepared else 0,
            return_basis=context.primary_return_basis,
        )
