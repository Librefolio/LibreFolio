"""Pure plugin tests for deterministic multi-asset risk analytics."""

from __future__ import annotations

import json
import math
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
from enum import StrEnum

import pytest
from pydantic import TypeAdapter, ValidationError

from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.portfolio import (
    DataQualityExcludedAsset,
    DataQualityExclusionReason,
    DataQualityReport,
)
from backend.app.schemas.risk import (
    AssetReturnPoint,
    AssetReturnSeries,
    AssetValuationPoint,
    AssetValuationSeries,
    PreparedAssetSeries,
    PreparedAssetSeriesSet,
    RiskAnalyticOutput,
    RiskComparisonOutput,
    RiskComparisonPoint,
    RiskCompositionPolicy,
    RiskDrawdownRecoveryStatus,
    RiskErrorCode,
    RiskExcludedAsset,
    RiskFreeReference,
    RiskHistoricalReplayAudit,
    RiskHistoricalReplayExclusionReason,
    RiskHistoricalReplayExclusionTreatment,
    RiskKpiOutput,
    RiskMode,
    RiskReturnBasis,
    RiskReturnOutput,
    RiskScopeKind,
    RiskSimulationProcess,
    RiskStressApplicationRule,
    RiskStressMethod,
    RiskValueStatus,
)
from backend.app.schemas.risk_scenarios import RiskScenarioDimension
from backend.app.services.data_quality_thresholds import STALE_PRICE_THRESHOLD_DAYS
from backend.app.services.provider_registry import RiskAnalyticRegistry
from backend.app.services.risk import acquired
from backend.app.services.risk import base as risk_base
from backend.app.services.risk.analytic_helpers import require_annualization_factor
from backend.app.services.risk.base import (
    RiskAnalytic,
    RiskAssetClassification,
    RiskExecutionContext,
    RiskHistoricalReplayContext,
    RiskUnavailableError,
)
from backend.app.services.risk.metrics import (
    annualized_expected_return,
    annualized_sharpe,
    annualized_sortino,
    annualized_volatility,
    beta,
    comparison_summary,
    current_buy_and_hold_returns,
    historical_var_cvar,
    pearson_correlation,
    summarize_drawdown,
)
from backend.app.services.risk.quant import models as simulation_models
from backend.app.services.risk.quant.engine import (
    MAX_HISTORY_CELLS,
    MAX_PORTFOLIO_CELLS,
    MAX_STOCHASTIC_CELLS,
    SimulationResourceLimitError,
    validate_resource_budget,
)
from backend.app.services.risk.quant.estimation import estimate_drift_uncertainty
from backend.app.services.risk.quant.models import SimulationEngineResult
from backend.app.services.risk.quant.optimization_engine import (
    clear_optimization_cache,
)
from backend.app.services.risk.quant.workers import (
    shutdown_quant_worker_pools,
)
from backend.app.services.risk_plugins import simulation as simulation_plugin_module
from backend.app.services.risk_plugins.asset_risk_return import (
    AssetRiskReturnAnalytic,
    AssetRiskReturnParams,
)
from backend.app.services.risk_plugins.comparison import (
    ComparisonAnalytic,
    ComparisonParams,
)
from backend.app.services.risk_plugins.correlation import (
    CorrelationAnalytic,
    CorrelationParams,
)
from backend.app.services.risk_plugins.drawdown_summary import (
    DrawdownSummaryAnalytic,
    DrawdownSummaryParams,
)
from backend.app.services.risk_plugins.historical_kpi import (
    HistoricalKpiAnalytic,
    HistoricalKpiParams,
)
from backend.app.services.risk_plugins.historical_var import (
    HistoricalVarAnalytic,
    HistoricalVarParams,
)
from backend.app.services.risk_plugins.portfolio_optimization import (
    PortfolioOptimizationAnalytic,
    PortfolioOptimizationParams,
)
from backend.app.services.risk_plugins.risk_contribution import (
    RiskContributionAnalytic,
    RiskContributionParams,
)
from backend.app.services.risk_plugins.simulation import (
    SimulationAnalytic,
    SimulationParams,
)
from backend.app.services.risk_plugins.stress import StressAnalytic, StressParams


def make_prepared_set(
    returns_by_asset: dict[int, list[float]],
    *,
    valuation_dates: list[date] | None = None,
) -> PreparedAssetSeriesSet:
    """Prepared series on one joint calendar: consecutive days from 1 January 2026 unless `valuation_dates` (baseline first) says otherwise."""
    observations = len(next(iter(returns_by_asset.values())))
    assert all(len(values) == observations for values in returns_by_asset.values())
    if valuation_dates is None:
        valuation_dates = [date(2026, 1, 1) + timedelta(days=index) for index in range(observations + 1)]
    assert len(valuation_dates) == observations + 1
    baseline = valuation_dates[0]
    return_dates = valuation_dates[1:]
    calendar_days = (return_dates[-1] - baseline).days
    prepared: list[PreparedAssetSeries] = []
    for asset_id, returns in returns_by_asset.items():
        wealth = Decimal("100")
        valuation_points = [
            AssetValuationPoint(
                valuation_date=baseline,
                effective_price_date=baseline,
                is_price_carried_forward=False,
                native_close=wealth,
                native_currency="EUR",
                target_close=wealth,
                target_currency="EUR",
            )
        ]
        return_points: list[AssetReturnPoint] = []
        for previous_date, current_date, value in zip(
            valuation_dates[:-1],
            valuation_dates[1:],
            returns,
            strict=True,
        ):
            wealth *= Decimal(str(1 + value))
            valuation_points.append(
                AssetValuationPoint(
                    valuation_date=current_date,
                    effective_price_date=current_date,
                    is_price_carried_forward=False,
                    native_close=wealth,
                    native_currency="EUR",
                    target_close=wealth,
                    target_currency="EUR",
                )
            )
            return_points.append(
                AssetReturnPoint(
                    date=current_date,
                    previous_valuation_date=previous_date,
                    value=value,
                )
            )
        prepared.append(
            PreparedAssetSeries(
                valuations=AssetValuationSeries(
                    asset_id=asset_id,
                    target_currency="EUR",
                    points=valuation_points,
                ),
                returns=AssetReturnSeries(
                    asset_id=asset_id,
                    target_currency="EUR",
                    points=return_points,
                ),
            )
        )
    return PreparedAssetSeriesSet(
        requested_range=DateRangeModel(start=return_dates[0], end=return_dates[-1]),
        baseline_date=baseline,
        effective_range=DateRangeModel(start=return_dates[0], end=return_dates[-1]),
        target_currency="EUR",
        series=prepared,
        joint_valuation_dates=valuation_dates,
        joint_return_dates=return_dates,
        n_observations=observations,
        calendar_days=calendar_days,
        annualization_factor=observations * 365 / calendar_days,
        calendar_coverage=1.0,
        fresh_quote_coverage=1.0,
        data_quality=DataQualityReport(),
        fx_fingerprint="0" * 64,
    )


def make_context(
    returns_by_asset: dict[int, list[float]],
    *,
    scope_kind: RiskScopeKind = RiskScopeKind.PORTFOLIO,
    mode: RiskMode = RiskMode.HISTORICAL,
    scope_asset_ids: tuple[int, ...] = (1, 2),
    primary_asset_id: int = 1,
    replay_source_asset_ids: dict[int, int] | None = None,
    replay_excluded_asset_ids: tuple[int, ...] = (),
    asset_classifications: dict[int, RiskAssetClassification] | None = None,
    geography_groups: dict[str, frozenset[str]] | None = None,
) -> RiskExecutionContext:
    prepared = make_prepared_set(returns_by_asset)
    primary = next(
        (item for item in prepared.series if item.returns.asset_id == primary_asset_id),
        prepared.series[0],
    )
    source_asset_ids = replay_source_asset_ids or {asset_id: asset_id for asset_id in scope_asset_ids if asset_id not in replay_excluded_asset_ids}
    return RiskExecutionContext(
        scope_kind=scope_kind,
        scope_reference=scope_kind.value,
        requested_range=prepared.requested_range,
        target_currency="EUR",
        mode=mode,
        composition_policy=RiskCompositionPolicy.CURRENT_BUY_AND_HOLD if mode == RiskMode.CURRENT_COMPOSITION else None,
        scope_asset_ids=scope_asset_ids,
        prepared_series=prepared,
        primary_baseline_date=prepared.baseline_date,
        primary_return_dates=tuple(point.date for point in primary.returns.points),
        primary_returns=tuple(float(point.value) for point in primary.returns.points),
        primary_return_basis=(RiskReturnBasis.TWRR if scope_kind == RiskScopeKind.PORTFOLIO and mode == RiskMode.HISTORICAL else RiskReturnBasis.PRICE_ONLY),
        annualization_factor=prepared.annualization_factor,
        calendar_days=prepared.calendar_days,
        coverage=prepared.calendar_coverage,
        data_quality=prepared.data_quality,
        requested_scope_asset_ids=scope_asset_ids,
        weights={1: 0.5, 2: 0.25},
        asset_values={1: Decimal("100"), 2: Decimal("50")},
        cash_weight=0.25,
        scope_value=Decimal("200"),
        historical_replay=RiskHistoricalReplayContext(
            prepared_series=prepared,
            source_asset_ids=source_asset_ids,
            excluded_asset_ids=replay_excluded_asset_ids,
            data_quality=prepared.data_quality,
        ),
        asset_classifications=asset_classifications or {asset_id: RiskAssetClassification(asset_class="OTHER") for asset_id in scope_asset_ids},
        geography_groups=geography_groups or {},
    )


def test_registry_discovers_all_deterministic_analytics():
    definitions = RiskAnalyticRegistry.list_definitions()
    assert [definition.analytic_code for definition in definitions] == [
        "asset_risk_return",
        # The weightless multi-asset family, for the ASSET_SET scope. Each one
        # serves a scope that has no aggregate series, so each publishes a list
        # of per-asset rows and no set-level figure.
        "asset_set_comparison",
        "asset_set_drawdown",
        "asset_set_kpi",
        "asset_set_risk_return",
        "asset_set_var",
        "comparison",
        "correlation",
        "drawdown_summary",
        "historical_kpi",
        "historical_var",
        "portfolio_optimization",
        "risk_contribution",
        "simulation",
        "stress",
    ]


# Each analytic declares the series it reads (developer's decision of 29/09/2026). On the portfolio
# TWRR, PRIMARY and PRIMARY_AND_BENCHMARK readers lose nothing when a scope asset has no series, so
# the service does not hand them the scope's exclusions; comparison keeps the per-asset data quality,
# because its benchmark is prepared on the scope's joint calendar. A new analytic reads the scope's
# assets unless it says otherwise.
PRIMARY_READERS = frozenset({"historical_kpi", "historical_var", "drawdown_summary"})
PRIMARY_AND_BENCHMARK_READERS = frozenset({"comparison"})


def test_each_analytic_declares_the_series_it_reads():
    # Read through the module: a missing enum must fail this test, not the collection of the file.
    inputs = risk_base.RiskSeriesInputs
    assert issubclass(inputs, StrEnum)
    assert {member.value for member in inputs} == {"primary", "primary_and_benchmark", "scope_assets"}
    assert RiskAnalytic.series_inputs is inputs.SCOPE_ASSETS

    declared = {code: RiskAnalyticRegistry.get_plugin(code).series_inputs for code in RiskAnalyticRegistry.list_plugin_codes()}

    assert (PRIMARY_READERS | PRIMARY_AND_BENCHMARK_READERS) <= set(declared)
    assert all(isinstance(value, inputs) for value in declared.values()), declared
    assert declared == {code: (inputs.PRIMARY if code in PRIMARY_READERS else inputs.PRIMARY_AND_BENCHMARK if code in PRIMARY_AND_BENCHMARK_READERS else inputs.SCOPE_ASSETS) for code in declared}
    # One declaration, not two.
    assert not hasattr(RiskAnalytic, "reads_scope_asset_series")


def test_historical_kpi_consumes_portfolio_twrr_and_observed_annualization():
    returns = [0.01, -0.005] * 10
    computation = HistoricalKpiAnalytic().compute(
        HistoricalKpiParams(),
        make_context({1: returns, 2: returns}),
    )
    output = computation.output

    assert output.volatility > 0
    assert output.max_drawdown <= 0
    assert output.max_drawdown_duration_days >= 0
    assert output.sharpe is not None
    assert computation.risk_free is not None
    assert computation.risk_free.annual_rate == 0
    assert computation.method == "historical_twrr"


def test_historical_kpi_consumes_asset_close_returns():
    returns = [0.02, -0.01] * 10
    computation = HistoricalKpiAnalytic().compute(
        HistoricalKpiParams(),
        make_context(
            {1: returns},
            scope_kind=RiskScopeKind.ASSET,
            scope_asset_ids=(1,),
        ),
    )

    assert computation.output.volatility > 0
    assert computation.output.max_drawdown < 0
    assert computation.output.sharpe is not None
    assert computation.output.sortino is not None
    assert computation.method == "historical_close_returns"
    assert HistoricalKpiAnalytic.supported_scopes == (
        RiskScopeKind.ASSET,
        RiskScopeKind.PORTFOLIO,
    )


def test_drawdown_summary_registers_canonical_capabilities():
    assert DrawdownSummaryAnalytic.analytic_code == "drawdown_summary"
    assert DrawdownSummaryAnalytic.output_kind.value == "drawdown"
    assert DrawdownSummaryAnalytic.supported_scopes == (
        RiskScopeKind.ASSET,
        RiskScopeKind.PORTFOLIO,
    )
    assert DrawdownSummaryAnalytic.supported_modes == (RiskMode.HISTORICAL,)
    assert DrawdownSummaryAnalytic.min_observations == 2
    assert DrawdownSummaryAnalytic.catalog_definition().name_i18n_key == "risk.analytics.drawdownSummary.name"


def test_drawdown_summary_asset_scope_uses_price_only_basis():
    returns = [0.05, -0.10, -0.05, 0.02, 0.01]
    computation = DrawdownSummaryAnalytic().compute(
        DrawdownSummaryParams(),
        make_context(
            {1: returns},
            scope_kind=RiskScopeKind.ASSET,
            scope_asset_ids=(1,),
        ),
    )
    output = computation.output
    assert output.kind.value == "drawdown"
    assert output.return_basis == RiskReturnBasis.PRICE_ONLY
    assert output.calculation_basis == "price_only_close"
    assert computation.method == "price_only_close"
    assert computation.return_basis == RiskReturnBasis.PRICE_ONLY
    assert output.maximum_drawdown < 0
    assert output.n_observations == len(returns)
    assert output.available_end >= output.available_start


def test_drawdown_summary_portfolio_twrr_external_cashflow_has_no_false_drawdown():
    # Flow-adjusted TWRR stays non-negative: contributions must not read as drawdown.
    returns = [0.004, 0.006, 0.003, 0.005, 0.002, 0.004]
    computation = DrawdownSummaryAnalytic().compute(
        DrawdownSummaryParams(),
        make_context({1: returns, 2: returns}),
    )
    output = computation.output
    assert output.return_basis == RiskReturnBasis.TWRR
    assert output.calculation_basis == "historical_twrr"
    assert output.maximum_drawdown_recovery_status == RiskDrawdownRecoveryStatus.NO_DRAWDOWN
    assert output.maximum_drawdown == 0
    assert output.current_drawdown == 0
    assert output.maximum_drawdown_peak_date is None
    assert output.maximum_drawdown_recovery_date is None


def test_drawdown_summary_broker_filtered_portfolio_reuses_twrr_path():
    returns = [0.01, -0.04, -0.02, 0.03]
    context = replace(
        make_context({1: returns, 2: returns}),
        broker_ids=(3, 7),
    )
    computation = DrawdownSummaryAnalytic().compute(DrawdownSummaryParams(), context)
    output = computation.output
    assert context.broker_ids == (3, 7)
    assert output.return_basis == RiskReturnBasis.TWRR
    assert output.calculation_basis == "historical_twrr"
    assert output.maximum_drawdown < 0


def test_drawdown_summary_requires_primary_history():
    context = replace(
        make_context({1: [0.01, -0.02], 2: [0.01, -0.02]}),
        primary_returns=(),
        primary_return_dates=(),
    )
    with pytest.raises(RiskUnavailableError):
        DrawdownSummaryAnalytic().compute(DrawdownSummaryParams(), context)


def test_drawdown_summary_output_serializes_through_discriminated_union():
    returns = [0.05, -0.20, -0.10, 0.60, -0.03]
    computation = DrawdownSummaryAnalytic().compute(
        DrawdownSummaryParams(),
        make_context(
            {1: returns},
            scope_kind=RiskScopeKind.ASSET,
            scope_asset_ids=(1,),
        ),
    )
    payload = computation.output.model_dump(mode="json")
    assert payload["kind"] == "drawdown"
    assert payload["maximum_drawdown_recovery_status"] == "recovered"
    assert payload["current_drawdown"] <= 0
    assert payload["return_basis"] == "price_only"
    varying = [0.01, -0.01] * 10
    flat = [0.0] * 20
    computation = CorrelationAnalytic().compute(
        CorrelationParams(),
        make_context(
            {1: varying, 2: flat},
            scope_kind=RiskScopeKind.ASSET_SET,
        ),
    )
    cells = {(cell.row_asset_id, cell.column_asset_id): cell for cell in computation.output.cells}

    assert cells[(1, 1)].value == pytest.approx(1)
    assert cells[(1, 1)].status == RiskValueStatus.OK
    assert cells[(1, 2)].value is None
    assert cells[(1, 2)].status == RiskValueStatus.UNDEFINED
    assert any(warning.code == "flat_series" for warning in computation.warnings)


def test_risk_contribution_preserves_negative_pctr_and_additivity():
    driver = [0.01, -0.01] * 10
    context = make_context(
        {
            1: [2 * value for value in driver],
            2: [-value for value in driver],
        },
        mode=RiskMode.CURRENT_COMPOSITION,
    )
    computation = RiskContributionAnalytic().compute(
        RiskContributionParams(),
        context,
    )
    output = computation.output

    assert sum(item.component_contribution for item in output.items) == pytest.approx(output.portfolio_volatility)
    assert sum(item.percentage_contribution for item in output.items) == pytest.approx(1)
    assert output.items[1].percentage_contribution < 0
    assert output.cash_weight == pytest.approx(0.25)


def _risk_return_returns() -> dict[int, list[float]]:
    """Two divergent series: one trending up, one falling hard.

    Divergence is the only condition under which "the whole" and "the weighted
    parts" can differ at all — buy-and-hold lets the winner grow into a larger
    share of the portfolio as the window runs. Two parallel series would make the
    distinction this fixture exists to expose invisible.
    """
    return {
        1: [round(0.012 + 0.010 * math.sin(index * 0.7), 10) for index in range(24)],
        2: [round(-0.011 + 0.018 * math.cos(index * 0.4), 10) for index in range(24)],
    }


def _risk_return_context() -> RiskExecutionContext:
    """A current-composition context whose primary series is the blend, not an asset.

    ``make_context`` points the primary at one prepared asset, which is what the
    historical modes do. ``current_composition`` does not: the service builds the
    scope series with ``current_buy_and_hold_returns`` and hands *that* over as the
    primary. Reproducing it here is what makes "the portfolio is not one of the
    items" true of the fixture as well as of production.
    """
    returns_by_asset = _risk_return_returns()
    context = make_context(returns_by_asset, mode=RiskMode.CURRENT_COMPOSITION)
    blend = current_buy_and_hold_returns(
        returns_by_asset,
        dict(context.weights),
        cash_weight=context.cash_weight,
    )
    return replace(context, primary_returns=tuple(blend))


def test_asset_risk_return_registers_canonical_capabilities():
    assert AssetRiskReturnAnalytic.analytic_code == "asset_risk_return"
    assert AssetRiskReturnAnalytic.output_kind.value == "risk_return"
    assert AssetRiskReturnAnalytic.supported_scopes == (RiskScopeKind.PORTFOLIO,)
    # A per-asset point is a statement about the mix held now. `historical` has one
    # TWRR curve and no composition to decompose, so offering it there would have to
    # invent weights — and the invented ones would be today's, which is this mode.
    assert AssetRiskReturnAnalytic.supported_modes == (RiskMode.CURRENT_COMPOSITION,)
    assert AssetRiskReturnAnalytic.min_observations == 20
    # 1.2.0 (k6, 06/10/2026): every point also states its own Sharpe and Sortino, charged at the
    # request's risk-free rate and target.
    assert AssetRiskReturnAnalytic.algorithm_version == "1.2.0"
    assert AssetRiskReturnAnalytic.catalog_definition().name_i18n_key == "risk.analytics.assetRiskReturn.name"


def test_asset_risk_return_weights_close_with_cash_and_are_not_renormalized():
    context = _risk_return_context()
    output = AssetRiskReturnAnalytic().compute(AssetRiskReturnParams(), context).output

    assert output.kind.value == "risk_return"
    assert [item.asset_id for item in output.items] == list(context.scope_asset_ids)
    assert all(item.weight == pytest.approx(context.weights[item.asset_id], abs=1e-15) for item in output.items)
    # Shares of net worth, the same denominator risk_contribution uses. A plot whose
    # bubbles sum to less than the whole is telling the truth about cash; one
    # renormalized to the invested part would close at 1 and say nothing about it.
    assert math.fsum(item.weight for item in output.items) + output.cash_weight == pytest.approx(1.0, abs=1e-12)
    assert math.fsum(item.weight for item in output.items) == pytest.approx(0.75, abs=1e-12)
    assert output.cash_weight == pytest.approx(0.25, abs=1e-12)


def test_asset_risk_return_measures_the_whole_on_the_primary_series_not_on_the_parts():
    context = _risk_return_context()
    annualization = context.annualization_factor
    output = AssetRiskReturnAnalytic().compute(AssetRiskReturnParams(), context).output

    assert output.portfolio_volatility == pytest.approx(annualized_volatility(context.primary_returns, annualization), rel=1e-12)
    assert output.portfolio_expected_annual_return == pytest.approx(annualized_expected_return(context.primary_returns, annualization), rel=1e-12)

    # Summing the parts is the plausible shortcut and it answers a different
    # question: the weights drift inside the window, so the weighted average of the
    # points is not the point of the whole. Both are right; only one is the portfolio.
    weighted_volatility = math.fsum(item.weight * item.volatility for item in output.items)
    weighted_expected = math.fsum(item.weight * item.expected_annual_return for item in output.items)
    assert output.portfolio_volatility != pytest.approx(weighted_volatility, rel=1e-6)
    assert output.portfolio_expected_annual_return != pytest.approx(weighted_expected, rel=1e-6)


def test_asset_risk_return_portfolio_pair_moves_with_the_primary_and_the_items_do_not():
    """The pin no weighted average of the items can satisfy.

    Scaling every primary return by two doubles both coordinates of the whole —
    mean and standard deviation are both homogeneous of degree one — while the
    prepared series behind the items is untouched, so every point stays put.
    """
    context = _risk_return_context()
    louder = replace(context, primary_returns=tuple(value * 2 for value in context.primary_returns))

    base = AssetRiskReturnAnalytic().compute(AssetRiskReturnParams(), context).output
    doubled = AssetRiskReturnAnalytic().compute(AssetRiskReturnParams(), louder).output

    assert [(item.asset_id, item.weight, item.volatility, item.expected_annual_return) for item in doubled.items] == [(item.asset_id, item.weight, item.volatility, item.expected_annual_return) for item in base.items]
    assert doubled.portfolio_volatility == pytest.approx(2 * base.portfolio_volatility, rel=1e-12)
    assert doubled.portfolio_expected_annual_return == pytest.approx(2 * base.portfolio_expected_annual_return, rel=1e-12)


def test_asset_risk_return_slope_through_a_zero_intercept_is_the_sharpe_ratio():
    """The geometry the arithmetic convention buys, asserted where it is published.

    ``metrics`` pins the identity on a bare series; this pins that the plugin
    publishes the pair that carries it, so a reader of the chart who measures the
    slope from the risk-free intercept reads the portfolio's own Sharpe ratio.
    """
    context = _risk_return_context()
    output = AssetRiskReturnAnalytic().compute(AssetRiskReturnParams(), context).output
    sharpe = annualized_sharpe(context.primary_returns, context.annualization_factor, annual_risk_free_rate=0.0)

    assert sharpe is not None
    assert output.portfolio_volatility > 0
    assert output.portfolio_expected_annual_return / output.portfolio_volatility == pytest.approx(sharpe, rel=1e-12)


def test_asset_risk_return_requires_a_current_weight_for_every_scope_asset():
    context = replace(_risk_return_context(), weights={1: 0.5})

    with pytest.raises(RiskUnavailableError) as exc_info:
        AssetRiskReturnAnalytic().compute(AssetRiskReturnParams(), context)

    assert exc_info.value.code == RiskErrorCode.DATA_UNAVAILABLE


def test_asset_risk_return_skips_a_point_it_cannot_measure_instead_of_calling_it_riskless():
    """One observation is a return without a dispersion, so it yields no point.

    ``PreparedAssetSeriesSet`` refuses a ragged calendar, so the only prepared set
    in which an asset owns a single observation is one where every asset does. The
    primary series is supplied separately — it is the blend, not a prepared asset —
    which is why it is replaced here rather than shortened with the rest.

    What the guard promises is the *absence* of a point: emitting a zero volatility
    would draw the holding on the vertical axis as if it carried no risk, which is a
    measurement nobody made.
    """
    single_observation = make_context({1: [0.03], 2: [-0.02]}, mode=RiskMode.CURRENT_COMPOSITION)
    context = replace(
        single_observation,
        primary_return_dates=tuple(date(2026, 1, 2) + timedelta(days=index) for index in range(3)),
        primary_returns=(0.01, -0.004, 0.006),
    )

    output = AssetRiskReturnAnalytic().compute(AssetRiskReturnParams(), context).output

    assert output.items == []
    assert output.cash_weight == pytest.approx(0.25, abs=1e-12)
    assert output.portfolio_volatility == pytest.approx(annualized_volatility(context.primary_returns, context.annualization_factor), rel=1e-12)


def test_asset_risk_return_output_survives_the_discriminated_union_round_trip():
    context = _risk_return_context()
    output = AssetRiskReturnAnalytic().compute(AssetRiskReturnParams(), context).output
    payload = output.model_dump(mode="json")

    assert payload["kind"] == "risk_return"
    assert [item["asset_id"] for item in payload["items"]] == list(context.scope_asset_ids)

    restored = TypeAdapter(RiskAnalyticOutput).validate_python(payload)

    assert isinstance(restored, RiskReturnOutput)
    assert restored.portfolio_volatility == pytest.approx(output.portfolio_volatility, rel=1e-12)
    assert restored.portfolio_expected_annual_return == pytest.approx(output.portfolio_expected_annual_return, rel=1e-12)
    assert restored.cash_weight == pytest.approx(output.cash_weight, rel=1e-12)
    assert [item.asset_id for item in restored.items] == [item.asset_id for item in output.items]


# --------------------------------------------------------------------------- #
# k6 — every risk/return point states its own Sharpe and Sortino (agreed with the Dashboard owner on
# 06/10/2026).
#
# `AssetRiskReturnParams` takes the two rates of `HistoricalKpiParams` — `risk_free_annual_rate` and
# `target_annual_return`, floats above -1, zero by default — and every item gains `sharpe` and
# `sortino`, measured with `annualized_sharpe` / `annualized_sortino` on the very returns and the very
# factor its `volatility` and `expected_annual_return` come from. So, with
# `rf_p = expm1(log1p(rf) / f)`, every point obeys `sharpe * volatility == expected - f * rf_p`: the
# intercept is `f * rf_p` (about ln(1 + rf)), not `rf`, and at rf = 0 the slope through the origin is
# the Sharpe ratio. Sortino is charged the target, never the risk-free rate. An undefined ratio is
# `None`, never 0, with one warning per condition naming the holdings, as `asset_set_kpi` does. The
# computation declares the rate it charged. Without parameters the numbers are those of rf = 0 and a
# zero target, and the portfolio-level fields do not move.
#
# Written red first: each case needs a parameter, a field or a declaration that k6 adds.
# --------------------------------------------------------------------------- #

RATIO_MIXED_ID = 1  # gains and losses: both ratios are defined
RATIO_GAINER_ID = 2  # moves, but never loses: a Sharpe, and no downside to divide by
RATIO_FLAT_ID = 3  # never moves: no volatility, no downside, neither ratio
RATIO_RETURNS = {
    RATIO_MIXED_ID: [round(0.004 * math.sin(index * 0.9) + 0.0006, 10) for index in range(24)],
    RATIO_GAINER_ID: [round(0.002 + 0.0015 * math.cos(index * 0.7), 10) for index in range(24)],
    RATIO_FLAT_ID: [0.0015] * 24,
}
RATIO_WEIGHTS = {RATIO_MIXED_ID: 0.4, RATIO_GAINER_ID: 0.3, RATIO_FLAT_ID: 0.2}
# The parameters as a request sends them. Wherever the two rates differ, a Sortino charged the
# risk-free rate instead of the target is a different number.
RATIO_RATES = [
    pytest.param({}, id="no-parameters"),
    pytest.param({"risk_free_annual_rate": 0.03}, id="risk-free-3pct"),
    pytest.param({"risk_free_annual_rate": 0.03, "target_annual_return": 0.05}, id="risk-free-3pct-target-5pct"),
]


def _ratio_context() -> RiskExecutionContext:
    """Today's composition of the three holdings above; the primary is their buy-and-hold blend."""
    context = make_context(RATIO_RETURNS, mode=RiskMode.CURRENT_COMPOSITION, scope_asset_ids=tuple(RATIO_RETURNS))
    blend = current_buy_and_hold_returns(RATIO_RETURNS, RATIO_WEIGHTS, cash_weight=0.1)
    return replace(context, weights=RATIO_WEIGHTS, cash_weight=0.1, primary_returns=tuple(blend))


def _assert_ratio(actual: float | None, expected: float | None, label: str) -> None:
    """A defined ratio to float precision; an undefined one as `None`, never as a number."""
    if expected is None:
        assert actual is None, f"{label}: {actual} published where the ratio is undefined"
    else:
        assert actual == pytest.approx(expected, rel=1e-12), label


def _validation_schema(model, field: str) -> dict:
    """What a parameter accepts — its type, default and bounds — without the hints a form reads."""
    schema = model.model_json_schema()["properties"][field]
    return {key: schema.get(key) for key in ("type", "default", "exclusiveMinimum", "minimum", "exclusiveMaximum", "maximum")}


def test_asset_risk_return_params_take_the_two_rates_of_historical_kpi():
    """The same two fields as `HistoricalKpiParams`: floats above -1, zero by default — and still nothing else."""
    defaults = AssetRiskReturnParams()
    assert (defaults.risk_free_annual_rate, defaults.target_annual_return) == (0.0, 0.0)
    charged = AssetRiskReturnAnalytic.validate_params({"risk_free_annual_rate": 0.03, "target_annual_return": 0.05})
    assert (charged.risk_free_annual_rate, charged.target_annual_return) == (0.03, 0.05)

    for field in ("risk_free_annual_rate", "target_annual_return"):
        assert _validation_schema(AssetRiskReturnParams, field) == _validation_schema(HistoricalKpiParams, field), field
        assert getattr(AssetRiskReturnAnalytic.validate_params({field: -0.99}), field) == -0.99
        with pytest.raises(ValidationError):
            AssetRiskReturnAnalytic.validate_params({field: -1.0})
    # Closed as before: a parameter it does not know is refused, never ignored.
    with pytest.raises(ValidationError):
        AssetRiskReturnAnalytic.validate_params({"risk_free_annual_rate": 0.03, "risk_free_rate": 0.03})


@pytest.mark.parametrize("rates", RATIO_RATES)
def test_asset_risk_return_gives_each_point_the_sharpe_and_sortino_of_its_own_coordinates(rates):
    """Each ratio is measured on the returns and the factor its point is drawn from.

    Two pins, one per half. The ratios are the metrics' own on the holding's prepared returns —
    neither the primary's nor another holding's. And the Sharpe ties back to the point printed beside
    it: the line from the intercept `f * rf_p` through (volatility, expected return) has it as its
    slope, which holds only if all three were measured on one series with one factor.
    """
    risk_free = rates.get("risk_free_annual_rate", 0.0)
    target = rates.get("target_annual_return", 0.0)
    context = _ratio_context()
    factor = context.annualization_factor
    expected = {asset_id: (annualized_sharpe(returns, factor, annual_risk_free_rate=risk_free), annualized_sortino(returns, factor, annual_target_return=target)) for asset_id, returns in RATIO_RETURNS.items()}
    # Premises, on the fixture alone: each ratio is defined somewhere and undefined somewhere, and a
    # Sortino charged the risk-free rate instead of the target would be another number.
    assert [sharpe is None for sharpe, _sortino in expected.values()] == [False, False, True]
    assert [sortino is None for _sharpe, sortino in expected.values()] == [False, True, True]
    if risk_free != target:
        assert annualized_sortino(RATIO_RETURNS[RATIO_MIXED_ID], factor, annual_target_return=risk_free) != pytest.approx(expected[RATIO_MIXED_ID][1], rel=1e-6)

    computation = AssetRiskReturnAnalytic().compute(AssetRiskReturnAnalytic.validate_params(rates), context)
    items = computation.output.items

    assert computation.annualization_factor == factor
    assert [item.asset_id for item in items] == list(RATIO_RETURNS)
    for item in items:
        sharpe, sortino = expected[item.asset_id]
        _assert_ratio(item.sharpe, sharpe, f"Sharpe of asset {item.asset_id}")
        _assert_ratio(item.sortino, sortino, f"Sortino of asset {item.asset_id}")

    period_rate = math.expm1(math.log1p(risk_free) / factor)
    for item in items:
        if item.sharpe is not None:
            assert item.sharpe * item.volatility == pytest.approx(item.expected_annual_return - factor * period_rate, rel=1e-12, abs=1e-15), item.asset_id


def test_asset_risk_return_reports_an_undefined_ratio_as_undefined_and_names_its_holdings():
    """`None` is the absence of a ratio; a `0` would be a measurement nobody made.

    As in `asset_set_kpi`: one warning per condition, naming every holding it applies to in the order
    of the points. The flat holding has neither ratio; the one that never loses has a Sharpe but no
    downside to divide by; the third keeps both and is named by neither warning.
    """
    computation = AssetRiskReturnAnalytic().compute(AssetRiskReturnAnalytic.validate_params({"risk_free_annual_rate": 0.03}), _ratio_context())
    items = {item.asset_id: item for item in computation.output.items}

    assert set(items) == set(RATIO_RETURNS)
    assert (items[RATIO_FLAT_ID].sharpe, items[RATIO_FLAT_ID].sortino) == (None, None)
    assert items[RATIO_GAINER_ID].sharpe is not None
    assert items[RATIO_GAINER_ID].sortino is None
    assert None not in (items[RATIO_MIXED_ID].sharpe, items[RATIO_MIXED_ID].sortino)
    warnings = [(warning.code, warning.message_i18n_key, warning.details.get("asset_ids")) for warning in computation.warnings]
    assert sorted(warnings) == [
        ("sharpe_undefined", "risk.warnings.sharpe_undefined_assets", [RATIO_FLAT_ID]),
        ("sortino_undefined", "risk.warnings.sortino_undefined_assets", [RATIO_GAINER_ID, RATIO_FLAT_ID]),
    ]

    # Nothing undefined, nothing said.
    quiet = AssetRiskReturnAnalytic().compute(AssetRiskReturnAnalytic.validate_params({"risk_free_annual_rate": 0.03}), replace(_ratio_context(), scope_asset_ids=(RATIO_MIXED_ID,)))
    assert [item.asset_id for item in quiet.output.items] == [RATIO_MIXED_ID]
    assert list(quiet.warnings) == []


def test_asset_risk_return_declares_the_risk_free_rate_it_charged():
    """As `historical_kpi` does: the rate the ratios were charged, where it came from, in the target currency."""
    context = replace(_ratio_context(), target_currency="CHF")

    charged = AssetRiskReturnAnalytic().compute(AssetRiskReturnAnalytic.validate_params({"risk_free_annual_rate": 0.03, "target_annual_return": 0.05}), context)
    implicit = AssetRiskReturnAnalytic().compute(AssetRiskReturnParams(), context)

    assert charged.risk_free == RiskFreeReference(annual_rate=0.03, source="analytic_param", currency="CHF")
    assert implicit.risk_free == RiskFreeReference(annual_rate=0.0, source="analytic_param", currency="CHF")


def test_asset_risk_return_rates_move_the_two_ratios_and_nothing_else():
    """Backward compatible by construction: without parameters nothing is charged, and a rate moves no coordinate.

    The rates enter the two ratios only. The points stay where they were — weight, volatility,
    expected return — and so does the portfolio's own pair, which gains no ratio of its own.
    """
    context = _ratio_context()
    implicit = AssetRiskReturnAnalytic().compute(AssetRiskReturnParams(), context).output
    explicit = AssetRiskReturnAnalytic().compute(AssetRiskReturnAnalytic.validate_params({"risk_free_annual_rate": 0.0, "target_annual_return": 0.0}), context).output
    charged = AssetRiskReturnAnalytic().compute(AssetRiskReturnAnalytic.validate_params({"risk_free_annual_rate": 0.03, "target_annual_return": 0.05}), context).output

    assert implicit.model_dump() == explicit.model_dump()
    ratios = {"items": {"__all__": {"sharpe", "sortino"}}}
    assert charged.model_dump(exclude=ratios) == implicit.model_dump(exclude=ratios)
    # ...and the ratios did move, so the equality above is not between two copies.
    mixed = [next(item for item in output.items if item.asset_id == RATIO_MIXED_ID) for output in (implicit, charged)]
    assert mixed[1].sharpe != pytest.approx(mixed[0].sharpe, rel=1e-6)
    assert mixed[1].sortino != pytest.approx(mixed[0].sortino, rel=1e-6)
    # Two fields more on each point, none on the whole.
    assert set(implicit.model_dump()) == {"kind", "portfolio_volatility", "portfolio_expected_annual_return", "cash_weight", "excluded_weight", "items"}
    assert all(set(item) == {"asset_id", "weight", "volatility", "expected_annual_return", "sharpe", "sortino"} for item in implicit.model_dump()["items"])


def test_comparison_measures_the_reference_on_the_common_days_it_reports():
    """The benchmark's own pair must come from the window beta came from.

    A reference routinely has more history than the series it is compared against —
    an index exists before the portfolio does. Beta and correlation already use the
    intersection; taking the reference's volatility from its full history would place
    the benchmark at a coordinate no observation in the reported window supports.

    The primary here starts late and ends early, so the days the reference owns alone
    sit on both sides of the window — and they are the loud ones.
    """
    quiet = [round(0.004 * math.sin(index * 0.5), 10) for index in range(30)]
    violent = [round(0.05 * math.cos(index * 0.9), 10) for index in range(30)]
    common = slice(4, 28)
    full_context = make_context(
        {1: quiet, 2: violent},
        scope_kind=RiskScopeKind.ASSET,
        scope_asset_ids=(1,),
    )
    context = replace(
        full_context,
        primary_baseline_date=full_context.primary_return_dates[common.start - 1],
        primary_return_dates=full_context.primary_return_dates[common],
        primary_returns=full_context.primary_returns[common],
    )

    computation = ComparisonAnalytic().compute(ComparisonParams(comparison_asset_id=2), context)
    output = computation.output
    common_returns = violent[common]
    annualization = computation.annualization_factor

    assert output.observations == len(common_returns)
    assert len(common_returns) < len(violent)
    assert output.comparison_volatility == pytest.approx(annualized_volatility(common_returns, annualization), rel=1e-12)
    assert output.comparison_expected_annual_return == pytest.approx(annualized_expected_return(common_returns, annualization), rel=1e-12)

    # The full history is the wrong window, and on this series it is a visibly
    # different number — which is what the assertion above would otherwise allow.
    assert output.comparison_volatility != pytest.approx(annualized_volatility(violent, annualization), rel=1e-6)
    assert output.comparison_expected_annual_return != pytest.approx(annualized_expected_return(violent, annualization), rel=1e-6)


def test_comparison_publishes_the_reference_pair_only_beside_a_beta_it_could_measure():
    """Same window, same factor, one contract: the diamond and the line agree.

    The reference's expected return is arithmetic, matching ``RiskReturnItem``, so
    the benchmark's slope through a zero intercept is its own Sharpe ratio on the
    common days. A compounded figure here would put the diamond off the line while
    every holding stayed on it.
    """
    returns = [round(0.003 * math.sin(index * 0.6) + 0.001, 10) for index in range(24)]
    reference = [round(0.006 * math.cos(index * 0.45) + 0.002, 10) for index in range(24)]
    context = make_context(
        {1: returns, 2: reference},
        scope_kind=RiskScopeKind.ASSET,
        scope_asset_ids=(1,),
    )

    computation = ComparisonAnalytic().compute(ComparisonParams(comparison_asset_id=2), context)
    output = computation.output
    annualization = computation.annualization_factor
    sharpe = annualized_sharpe(reference, annualization, annual_risk_free_rate=0.0)

    assert output.observations == len(reference)
    assert output.beta is not None
    assert sharpe is not None
    assert output.comparison_volatility is not None
    assert output.comparison_volatility > 0
    assert output.comparison_expected_annual_return is not None
    assert output.comparison_expected_annual_return / output.comparison_volatility == pytest.approx(sharpe, rel=1e-12)


# --------------------------------------------------------------------------- #
# Comparison pairs each primary return with the benchmark's return over the same span
# (developer's decision of 30/09/2026).
#
# A primary return dated D_i spans (D_{i-1}, D_i], the first from the primary's own
# baseline. Since round 1 the portfolio TWRR is read on observation days only, so a
# benchmark quoted on more days than the holdings — a crypto's weekends, a US ETF on an
# EU holiday — has several returns inside one primary span. They are compounded into
# the pair; a date-by-date match kept the last and lost the others. A span holding one
# benchmark return uses it as it is, so one shared calendar is unchanged to the byte.
# Before the first pair, a primary date the benchmark has no return on is dropped and the
# span starts at it. After the first pair it is no boundary (contract C): at the next date
# both series share, each is compounded over (last paired date, D]. The annualization
# baseline is the first pair's span start.
# --------------------------------------------------------------------------- #

COMPARISON_BENCHMARK_ID = 2
SPAN_BASELINE = date(2026, 1, 2)  # a Friday: the primary's baseline
SPAN_END = date(2026, 2, 13)  # a Friday, six weeks on
SPAN_EVERY_DAY = [SPAN_BASELINE + timedelta(days=offset) for offset in range((SPAN_END - SPAN_BASELINE).days + 1)]
SPAN_WEEKDAYS = [day for day in SPAN_EVERY_DAY[1:] if day.weekday() < 5]  # the primary's 30 dates
SPAN_PRIMARY_RETURNS = [round(0.005 * math.cos(index * 0.9) + 0.0005, 10) for index in range(len(SPAN_WEEKDAYS))]
# The benchmark moves every calendar day, weekends included.
SPAN_BENCHMARK_EVERY_DAY = [round(0.004 * math.sin(index * 0.7 + 0.2) + 0.0015 * math.cos(index * 2.1), 10) for index in range(len(SPAN_EVERY_DAY) - 1)]


def span_context(benchmark_dates: list[date], benchmark_returns: list[float]) -> RiskExecutionContext:
    """A portfolio TWRR read on `SPAN_WEEKDAYS` from `SPAN_BASELINE`, beside a benchmark prepared on its own calendar."""
    calendar_days = (SPAN_WEEKDAYS[-1] - SPAN_BASELINE).days
    return replace(
        make_context({1: SPAN_PRIMARY_RETURNS, COMPARISON_BENCHMARK_ID: SPAN_PRIMARY_RETURNS}, scope_asset_ids=(1,)),
        prepared_series=make_prepared_set({COMPARISON_BENCHMARK_ID: benchmark_returns}, valuation_dates=[SPAN_BASELINE, *benchmark_dates]),
        primary_baseline_date=SPAN_BASELINE,
        primary_return_dates=tuple(SPAN_WEEKDAYS),
        primary_returns=tuple(SPAN_PRIMARY_RETURNS),
        calendar_days=calendar_days,
        annualization_factor=len(SPAN_WEEKDAYS) * 365 / calendar_days,
    )


def benchmark_move(own: dict[date, float], start: date, end: date) -> float:
    """The benchmark's own return over (start, end]: its returns dated inside, compounded."""
    return math.prod(1 + value for day, value in own.items() if start < day <= end) - 1


def test_comparison_compounds_the_benchmark_moves_inside_each_primary_span():
    own = dict(zip(SPAN_EVERY_DAY[1:], SPAN_BENCHMARK_EVERY_DAY, strict=True))
    assert all(value != 0.0 for day, value in own.items() if day.weekday() >= 5)  # the weekend moves are real

    computation = ComparisonAnalytic().compute(ComparisonParams(comparison_asset_id=COMPARISON_BENCHMARK_ID), span_context(SPAN_EVERY_DAY[1:], SPAN_BENCHMARK_EVERY_DAY))
    output = computation.output
    cumulative = {point.date: point.comparison_cumulative_return for point in output.series}

    # The first span runs from the primary's baseline: Friday to Monday holds Saturday, Sunday and Monday.
    first = SPAN_WEEKDAYS[0]
    assert (SPAN_BASELINE.weekday(), first.weekday()) == (4, 0)
    assert cumulative[first] == pytest.approx(benchmark_move(own, SPAN_BASELINE, first), rel=1e-12)
    # Every later Monday pairs with the weekend before it: (1 + cumulative on Monday) / (1 + cumulative on Friday) − 1.
    friday, monday = date(2026, 1, 9), date(2026, 1, 12)
    assert (1 + cumulative[monday]) / (1 + cumulative[friday]) - 1 == pytest.approx(benchmark_move(own, friday, monday), rel=1e-12)
    # Over the window the benchmark returns exactly what it returned: none of its moves is lost.
    assert cumulative[SPAN_END] == pytest.approx(math.prod(1 + value for value in SPAN_BENCHMARK_EVERY_DAY) - 1, rel=1e-12)
    assert output.observations == computation.n_observations == len(SPAN_WEEKDAYS)
    assert computation.coverage == 1.0

    # Everything downstream reads the pairs, annualized from the first pair's span start.
    pairs = [benchmark_move(own, start, end) for start, end in zip([SPAN_BASELINE, *SPAN_WEEKDAYS[:-1]], SPAN_WEEKDAYS, strict=True)]
    factor = len(SPAN_WEEKDAYS) * 365 / (SPAN_END - SPAN_BASELINE).days
    summary = comparison_summary(SPAN_PRIMARY_RETURNS, pairs, factor)
    assert computation.calendar_days == (SPAN_END - SPAN_BASELINE).days
    assert computation.annualization_factor == pytest.approx(factor, rel=1e-12)
    assert [output.active_return, output.tracking_error, output.information_ratio, output.correlation, output.beta] == pytest.approx([summary.active_return, summary.tracking_error, summary.information_ratio, summary.correlation, summary.beta], rel=1e-12)
    assert output.comparison_volatility == pytest.approx(annualized_volatility(pairs, factor), rel=1e-12)
    assert output.comparison_expected_annual_return == pytest.approx(annualized_expected_return(pairs, factor), rel=1e-12)
    assert [point.comparison_drawdown for point in output.series] == pytest.approx(summary.comparison_drawdowns, rel=1e-12, abs=1e-15)


# What k6 adds to the comparison payload (06/10/2026). Every other field is one comparison published before
# k6, and the date-match pin below holds them to the bit; the three k6 fields have tests of their own.
K6_COMPARISON_FIELDS = {"comparison_sharpe", "comparison_sortino", "items"}


@pytest.mark.parametrize(
    ("scope_kind", "mode"),
    [
        pytest.param(RiskScopeKind.ASSET, RiskMode.HISTORICAL, id="asset"),
        pytest.param(RiskScopeKind.PORTFOLIO, RiskMode.CURRENT_COMPOSITION, id="portfolio-current-composition"),
    ],
)
def test_comparison_on_one_shared_calendar_is_the_date_match_to_the_byte(scope_kind, mode):
    primary = [round(0.004 * math.sin(index * 0.8) + 0.0007, 10) for index in range(30)]
    reference = [round(0.006 * math.cos(index * 0.55) - 0.0003, 10) for index in range(30)]
    # A single return re-derived as (1 + r) − 1 differs from r in its last bits here, so the pin can see one.
    assert any((1 + value) - 1 != value for value in reference)
    context = make_context({1: primary, COMPARISON_BENCHMARK_ID: reference}, scope_kind=scope_kind, mode=mode, scope_asset_ids=(1,))

    computation = ComparisonAnalytic().compute(ComparisonParams(comparison_asset_id=COMPARISON_BENCHMARK_ID), context)

    # The date match, computed here: each date's two returns as they are, from the shared baseline.
    dates = context.primary_return_dates
    calendar_days = (dates[-1] - context.primary_baseline_date).days
    factor = len(dates) * 365 / calendar_days
    summary = comparison_summary(primary, reference, factor)
    expected = RiskComparisonOutput(
        comparison_asset_id=COMPARISON_BENCHMARK_ID,
        active_return=summary.active_return,
        tracking_error=summary.tracking_error,
        information_ratio=summary.information_ratio,
        correlation=summary.correlation,
        beta=summary.beta,
        observations=len(dates),
        comparison_volatility=annualized_volatility(reference, factor),
        comparison_expected_annual_return=annualized_expected_return(reference, factor),
        series=[
            RiskComparisonPoint(date=day, primary_cumulative_return=primary_cumulative, comparison_cumulative_return=comparison_cumulative, primary_drawdown=primary_drawdown, comparison_drawdown=comparison_drawdown)
            for day, primary_cumulative, comparison_cumulative, primary_drawdown, comparison_drawdown in zip(dates, summary.primary_cumulative, summary.comparison_cumulative, summary.primary_drawdowns, summary.comparison_drawdowns, strict=True)
        ],
    )
    assert computation.output.model_dump(exclude=K6_COMPARISON_FIELDS) == expected.model_dump(exclude=K6_COMPARISON_FIELDS)
    assert computation.output.model_dump_json(exclude=K6_COMPARISON_FIELDS) == expected.model_dump_json(exclude=K6_COMPARISON_FIELDS)  # the same payload, bit for bit
    assert (computation.n_observations, computation.calendar_days, computation.annualization_factor, computation.coverage) == (len(dates), calendar_days, factor, 1.0)


@pytest.mark.parametrize(
    ("dropped", "first_span_start"),
    [
        # The start rule: before the first pair, the dropped date moves the span start to itself. A
        # date dropped after a pair follows contract C instead (the test after this one).
        pytest.param(date(2026, 1, 5), date(2026, 1, 5), id="the-first-primary-date"),
    ],
)
def test_comparison_drops_a_primary_date_the_benchmark_lacks_and_starts_the_next_span_at_it(dropped, first_span_start):
    # The benchmark trades the weekend before `dropped` but has no return dated on it, and no other weekend.
    weekend = [dropped - timedelta(days=2), dropped - timedelta(days=1)]
    benchmark_dates = sorted({*SPAN_WEEKDAYS, *weekend} - {dropped})
    benchmark_returns = [round(0.005 * math.sin(index * 0.65 + 0.4), 10) for index in range(len(benchmark_dates))]
    own = dict(zip(benchmark_dates, benchmark_returns, strict=True))

    computation = ComparisonAnalytic().compute(ComparisonParams(comparison_asset_id=COMPARISON_BENCHMARK_ID), span_context(benchmark_dates, benchmark_returns))
    output = computation.output

    kept = [day for day in SPAN_WEEKDAYS if day != dropped]
    assert [point.date for point in output.series] == kept
    assert output.observations == computation.n_observations == len(kept)
    assert computation.coverage == pytest.approx(len(kept) / len(SPAN_WEEKDAYS))
    # The next span is (dropped, Tuesday]: the benchmark's Tuesday return alone. The weekend moves sat in
    # the dropped span and leave with it, rather than being folded into Tuesday.
    tuesday = dropped + timedelta(days=1)
    position = kept.index(tuesday)
    before = output.series[position - 1].comparison_cumulative_return if position else 0.0
    assert (1 + output.series[position].comparison_cumulative_return) / (1 + before) - 1 == pytest.approx(own[tuesday], rel=1e-12)
    # The primary's return on the dropped date leaves too.
    primary = dict(zip(SPAN_WEEKDAYS, SPAN_PRIMARY_RETURNS, strict=True))
    assert output.series[-1].primary_cumulative_return == pytest.approx(math.prod(1 + primary[day] for day in kept) - 1, rel=1e-12)
    # The annualization baseline is the first pair's span start.
    factor = len(kept) * 365 / (SPAN_END - first_span_start).days
    assert computation.calendar_days == (SPAN_END - first_span_start).days
    assert computation.annualization_factor == pytest.approx(factor, rel=1e-12)
    assert output.comparison_volatility == pytest.approx(annualized_volatility([own[day] for day in kept], factor), rel=1e-12)


@pytest.mark.parametrize(
    ("dropped", "inside_the_gap"),
    [
        # Primary returns dated 5, 6 and 7 January; benchmark returns dated 5 and 7, the latter spanning 5→7.
        pytest.param(date(2026, 1, 6), [], id="the-benchmark-is-silent-in-the-gap"),
        # The benchmark trades the weekend before a Monday it has no return on.
        pytest.param(date(2026, 1, 12), [date(2026, 1, 10), date(2026, 1, 11)], id="a-monday-inside-the-window"),
    ],
)
def test_comparison_compounds_both_series_across_a_primary_date_the_benchmark_lacks_after_the_first_pair(dropped, inside_the_gap):
    """Contract C: after the first pair, both series are compounded between the dates they share.

    Once a pair exists, a primary date without a benchmark return is no span boundary: the span stays
    anchored on the last paired date, and at the next shared date the primary's returns and the
    benchmark's returns dated inside (anchor, D] are compounded, each on its own side. The two sides of
    a pair then always span the same days, and nothing either series returned is lost.
    """
    assert SPAN_WEEKDAYS.index(dropped) > 0  # the gap follows a pair: the start rule is not in play
    benchmark_dates = sorted({*SPAN_WEEKDAYS, *inside_the_gap} - {dropped})
    benchmark_returns = [round(0.005 * math.sin(index * 0.65 + 0.4), 10) for index in range(len(benchmark_dates))]
    own = dict(zip(benchmark_dates, benchmark_returns, strict=True))
    primary = dict(zip(SPAN_WEEKDAYS, SPAN_PRIMARY_RETURNS, strict=True))
    anchor = SPAN_WEEKDAYS[SPAN_WEEKDAYS.index(dropped) - 1]  # the last paired date before the gap
    joined = SPAN_WEEKDAYS[SPAN_WEEKDAYS.index(dropped) + 1]  # the next date both series share

    computation = ComparisonAnalytic().compute(ComparisonParams(comparison_asset_id=COMPARISON_BENCHMARK_ID), span_context(benchmark_dates, benchmark_returns))
    output = computation.output
    by_date = {point.date: point for point in output.series}

    kept = [day for day in SPAN_WEEKDAYS if day != dropped]
    assert [point.date for point in output.series] == kept
    # The pair on `joined` spans (anchor, joined] on both sides: the primary across the dropped date...
    assert (1 + by_date[joined].primary_cumulative_return) / (1 + by_date[anchor].primary_cumulative_return) - 1 == pytest.approx((1 + primary[dropped]) * (1 + primary[joined]) - 1, rel=1e-12)
    # ...and the benchmark over the same days, whatever it returned inside the gap.
    assert (1 + by_date[joined].comparison_cumulative_return) / (1 + by_date[anchor].comparison_cumulative_return) - 1 == pytest.approx(benchmark_move(own, anchor, joined), rel=1e-12)
    # Nothing either series returned is lost.
    assert output.series[-1].primary_cumulative_return == pytest.approx(math.prod(1 + value for value in SPAN_PRIMARY_RETURNS) - 1, rel=1e-12)
    assert output.series[-1].comparison_cumulative_return == pytest.approx(math.prod(1 + value for value in benchmark_returns) - 1, rel=1e-12)
    assert output.observations == computation.n_observations == len(kept)
    assert computation.coverage == pytest.approx(len(kept) / len(SPAN_WEEKDAYS))

    # Everything downstream reads the pairs, annualized from the first pair's span start.
    primary_pairs = [primary[day] for day in kept]
    benchmark_pairs = [own[day] for day in kept]
    primary_pairs[kept.index(joined)] = (1 + primary[dropped]) * (1 + primary[joined]) - 1
    benchmark_pairs[kept.index(joined)] = benchmark_move(own, anchor, joined)
    factor = len(kept) * 365 / (SPAN_END - SPAN_BASELINE).days
    summary = comparison_summary(primary_pairs, benchmark_pairs, factor)
    assert computation.calendar_days == (SPAN_END - SPAN_BASELINE).days
    assert computation.annualization_factor == pytest.approx(factor, rel=1e-12)
    assert [output.active_return, output.tracking_error, output.correlation, output.beta] == pytest.approx([summary.active_return, summary.tracking_error, summary.correlation, summary.beta], rel=1e-12)
    assert output.comparison_volatility == pytest.approx(annualized_volatility(benchmark_pairs, factor), rel=1e-12)


def test_comparison_pairing_by_span_is_a_new_algorithm_version():
    # 1.1.0 paired the two series by span. 1.2.0 (k6, 06/10/2026) adds the benchmark's own Sharpe and
    # Sortino and, on a portfolio scope, one beta and correlation per holding.
    assert ComparisonAnalytic.algorithm_version == "1.2.0"


# --------------------------------------------------------------------------- #
# k6 — the benchmark's own ratios, and one beta and correlation per holding (agreed with the Dashboard
# owner on 06/10/2026).
#
# `ComparisonParams` takes the two rates of `HistoricalKpiParams` (zero by default, above -1) and stays
# closed. `comparison_sharpe` / `comparison_sortino` are the benchmark's own ratios on exactly the paired
# returns and the factor `comparison_volatility` / `comparison_expected_annual_return` are measured on,
# so `comparison_sharpe * comparison_volatility == comparison_expected_annual_return - f * rf_p`;
# undefined, each is `None` with a `sharpe_undefined` / `sortino_undefined` warning naming the
# benchmark. On a portfolio scope `items` holds one `{asset_id, beta, correlation}` per held asset with
# a prepared series — never the benchmark itself (D371) — in asset id order, each holding paired with
# the benchmark as the primary is; on an asset scope it is empty. A flat holding has a measured beta of
# zero and no correlation, named by the per-asset correlation warning; a flat benchmark leaves every
# holding undefined, and only the two singular warnings speak for them.
# --------------------------------------------------------------------------- #

HOLDING_BENCHMARK_ID = 9
HOLDING_OBSERVATIONS = 30
HOLDING_RETURNS = {
    1: [round(0.006 * math.sin(index * 0.8) + 0.0008, 10) for index in range(HOLDING_OBSERVATIONS)],
    2: [round(0.004 * math.cos(index * 0.5) - 0.0002, 10) for index in range(HOLDING_OBSERVATIONS)],
    3: [round(0.009 * math.sin(index * 0.3 + 0.5) + 0.0004, 10) for index in range(HOLDING_OBSERVATIONS)],
}
# Gains and losses, so its own Sharpe and Sortino are both defined.
HOLDING_BENCHMARK = [round(0.005 * math.sin(index * 0.7 + 0.2) + 0.003 * math.cos(index * 1.3), 10) for index in range(HOLDING_OBSERVATIONS)]


def holdings_context(
    holdings: dict[int, list[float]] | None = None,
    *,
    benchmark: list[float] | None = None,
    scope_asset_ids: tuple[int, ...] | None = None,
    mode: RiskMode = RiskMode.CURRENT_COMPOSITION,
) -> RiskExecutionContext:
    """A portfolio of `holdings`, prepared on one joint calendar with the benchmark; the primary is their blend.

    One calendar for every series, so every pairing — the primary's and each holding's — is the date
    match, whatever the mode.
    """
    holdings = HOLDING_RETURNS if holdings is None else holdings
    benchmark = HOLDING_BENCHMARK if benchmark is None else benchmark
    scope = tuple(holdings) if scope_asset_ids is None else scope_asset_ids
    context = make_context({**holdings, HOLDING_BENCHMARK_ID: benchmark}, mode=mode, scope_asset_ids=scope)
    blend = current_buy_and_hold_returns(holdings, dict.fromkeys(holdings, 0.9 / len(holdings)), cash_weight=0.1)
    return replace(context, primary_returns=tuple(blend))


def compare_holdings(context: RiskExecutionContext, **rates: float):
    """`comparison` against the holdings' benchmark, with the rates as a request sends them."""
    return ComparisonAnalytic().compute(ComparisonAnalytic.validate_params({"comparison_asset_id": HOLDING_BENCHMARK_ID, **rates}), context)


def test_comparison_params_take_the_two_rates_of_historical_kpi():
    """Zero by default and above -1, as on the KPI; the benchmark is still required, and the model still closed."""
    defaults = ComparisonParams(comparison_asset_id=2)
    assert (defaults.risk_free_annual_rate, defaults.target_annual_return) == (0.0, 0.0)
    charged = ComparisonAnalytic.validate_params({"comparison_asset_id": 2, "risk_free_annual_rate": 0.03, "target_annual_return": 0.05})
    assert (charged.comparison_asset_id, charged.risk_free_annual_rate, charged.target_annual_return) == (2, 0.03, 0.05)

    for field in ("risk_free_annual_rate", "target_annual_return"):
        assert _validation_schema(ComparisonParams, field) == _validation_schema(HistoricalKpiParams, field), field
        assert getattr(ComparisonAnalytic.validate_params({"comparison_asset_id": 2, field: -0.99}), field) == -0.99
        with pytest.raises(ValidationError):
            ComparisonAnalytic.validate_params({"comparison_asset_id": 2, field: -1.0})
    with pytest.raises(ValidationError):
        ComparisonAnalytic.validate_params({"risk_free_annual_rate": 0.03})
    # An unknown parameter is still refused: the service turns this into `invalid_parameters`.
    with pytest.raises(ValidationError):
        ComparisonAnalytic.validate_params({"comparison_asset_id": 2, "risk_free_rate": 0.03})


@pytest.mark.parametrize("rates", RATIO_RATES)
def test_comparison_states_the_benchmark_own_sharpe_and_sortino_on_the_pairs_it_measured(rates):
    """The benchmark's ratios come from the pairs its volatility and expected return come from.

    On the span fixture the benchmark also moves at weekends, so a pair compounds several of its days:
    its raw daily series gives other ratios, and a Sharpe measured there would leave the diamond off
    the line through its own point.
    """
    risk_free = rates.get("risk_free_annual_rate", 0.0)
    target = rates.get("target_annual_return", 0.0)
    own = dict(zip(SPAN_EVERY_DAY[1:], SPAN_BENCHMARK_EVERY_DAY, strict=True))
    pairs = [benchmark_move(own, start, end) for start, end in zip([SPAN_BASELINE, *SPAN_WEEKDAYS[:-1]], SPAN_WEEKDAYS, strict=True)]
    factor = len(SPAN_WEEKDAYS) * 365 / (SPAN_END - SPAN_BASELINE).days
    sharpe = annualized_sharpe(pairs, factor, annual_risk_free_rate=risk_free)
    sortino = annualized_sortino(pairs, factor, annual_target_return=target)
    # Premises: both defined on the pairs, and neither is what the unpaired series or a swapped rate gives.
    assert sharpe is not None
    assert sortino is not None
    assert annualized_sharpe(SPAN_BENCHMARK_EVERY_DAY, factor, annual_risk_free_rate=risk_free) != pytest.approx(sharpe, rel=1e-6)
    if risk_free != target:
        assert annualized_sortino(pairs, factor, annual_target_return=risk_free) != pytest.approx(sortino, rel=1e-6)

    computation = ComparisonAnalytic().compute(
        ComparisonAnalytic.validate_params({"comparison_asset_id": COMPARISON_BENCHMARK_ID, **rates}),
        span_context(SPAN_EVERY_DAY[1:], SPAN_BENCHMARK_EVERY_DAY),
    )
    output = computation.output

    assert computation.annualization_factor == pytest.approx(factor, rel=1e-12)
    assert output.comparison_sharpe == pytest.approx(sharpe, rel=1e-12)
    assert output.comparison_sortino == pytest.approx(sortino, rel=1e-12)
    # The diamond's own line: from the intercept f * rf_p through (volatility, expected return).
    period_rate = math.expm1(math.log1p(risk_free) / computation.annualization_factor)
    assert output.comparison_sharpe * output.comparison_volatility == pytest.approx(output.comparison_expected_annual_return - computation.annualization_factor * period_rate, rel=1e-12, abs=1e-15)


def test_comparison_rates_move_the_benchmark_ratios_and_nothing_else():
    """Without rates nothing is charged; with them only the benchmark's two ratios move — no beta, no item, no point."""
    context = holdings_context()
    implicit = compare_holdings(context).output
    explicit = compare_holdings(context, risk_free_annual_rate=0.0, target_annual_return=0.0).output
    charged = compare_holdings(context, risk_free_annual_rate=0.03, target_annual_return=0.05).output

    assert implicit.model_dump() == explicit.model_dump()
    ratios = {"comparison_sharpe", "comparison_sortino"}
    assert charged.model_dump(exclude=ratios) == implicit.model_dump(exclude=ratios)
    assert charged.comparison_sharpe != pytest.approx(implicit.comparison_sharpe, rel=1e-6)
    assert charged.comparison_sortino != pytest.approx(implicit.comparison_sortino, rel=1e-6)


def test_comparison_declares_the_risk_free_rate_it_charged():
    """As `historical_kpi` and `asset_risk_return` do: the rate the benchmark's Sharpe was charged, where it came from, in the target currency."""
    context = replace(holdings_context(), target_currency="CHF")

    charged = compare_holdings(context, risk_free_annual_rate=0.03, target_annual_return=0.05)
    implicit = compare_holdings(context)

    assert charged.risk_free == RiskFreeReference(annual_rate=0.03, source="analytic_param", currency="CHF")
    assert implicit.risk_free == RiskFreeReference(annual_rate=0.0, source="analytic_param", currency="CHF")


def test_comparison_with_default_rates_keeps_every_field_it_published_before_k6():
    """The pin, on the holdings fixture: whatever comparison published before k6 is still the date match, to the bit.

    The scope holds three assets and the benchmark itself, so the per-holding work k6 adds runs on
    this payload; none of it may move a field that was already there. Green before k6, and meant to
    stay green after it.
    """
    context = holdings_context(scope_asset_ids=(3, 1, HOLDING_BENCHMARK_ID, 2))

    computation = ComparisonAnalytic().compute(ComparisonParams(comparison_asset_id=HOLDING_BENCHMARK_ID), context)

    dates = context.primary_return_dates
    calendar_days = (dates[-1] - context.primary_baseline_date).days
    factor = len(dates) * 365 / calendar_days
    primary = list(context.primary_returns)
    summary = comparison_summary(primary, HOLDING_BENCHMARK, factor)
    expected = RiskComparisonOutput(
        comparison_asset_id=HOLDING_BENCHMARK_ID,
        active_return=summary.active_return,
        tracking_error=summary.tracking_error,
        information_ratio=summary.information_ratio,
        correlation=summary.correlation,
        beta=summary.beta,
        observations=len(dates),
        comparison_volatility=annualized_volatility(HOLDING_BENCHMARK, factor),
        comparison_expected_annual_return=annualized_expected_return(HOLDING_BENCHMARK, factor),
        series=[
            RiskComparisonPoint(date=day, primary_cumulative_return=primary_cumulative, comparison_cumulative_return=comparison_cumulative, primary_drawdown=primary_drawdown, comparison_drawdown=comparison_drawdown)
            for day, primary_cumulative, comparison_cumulative, primary_drawdown, comparison_drawdown in zip(dates, summary.primary_cumulative, summary.comparison_cumulative, summary.primary_drawdowns, summary.comparison_drawdowns, strict=True)
        ],
    )
    assert computation.output.model_dump(exclude=K6_COMPARISON_FIELDS) == expected.model_dump(exclude=K6_COMPARISON_FIELDS)
    assert computation.output.model_dump_json(exclude=K6_COMPARISON_FIELDS) == expected.model_dump_json(exclude=K6_COMPARISON_FIELDS)
    assert (computation.method, computation.comparison_asset_id, computation.return_basis) == ("comparison_asset", HOLDING_BENCHMARK_ID, context.primary_return_basis)
    assert (computation.n_observations, computation.calendar_days, computation.annualization_factor, computation.coverage) == (len(dates), calendar_days, factor, 1.0)
    # Every figure is defined on this fixture, so nothing has a reason to warn.
    assert list(computation.warnings) == []


@pytest.mark.parametrize("mode", [pytest.param(RiskMode.CURRENT_COMPOSITION, id="current-composition"), pytest.param(RiskMode.HISTORICAL, id="historical")])
def test_comparison_measures_every_holding_against_the_benchmark_in_asset_id_order(mode):
    """One beta and one correlation per holding, each on its own returns paired with the benchmark's.

    On one joint calendar every pairing is the date match, so each figure is the plain metric of the
    two series. The holdings come in out of order, and their figures differ from each other and from
    the portfolio's own: neither the scope's order nor a copied portfolio beta can pass.
    """
    context = holdings_context(scope_asset_ids=(3, 1, 2), mode=mode)
    expected = {asset_id: (beta(returns, HOLDING_BENCHMARK), pearson_correlation(returns, HOLDING_BENCHMARK)) for asset_id, returns in HOLDING_RETURNS.items()}
    portfolio_beta = beta(list(context.primary_returns), HOLDING_BENCHMARK)
    assert len({round(value, 9) for value, _correlation in expected.values()} | {round(portfolio_beta, 9)}) == 4
    assert len({round(correlation, 9) for _value, correlation in expected.values()}) == 3

    output = compare_holdings(context).output

    # The portfolio's own beta is what it was.
    assert output.beta == pytest.approx(portfolio_beta, rel=1e-12)
    assert [item.asset_id for item in output.items] == [1, 2, 3]
    for item in output.items:
        holding_beta, holding_correlation = expected[item.asset_id]
        assert item.beta == pytest.approx(holding_beta, rel=1e-12), item.asset_id
        assert item.correlation == pytest.approx(holding_correlation, rel=1e-12), item.asset_id


def test_comparison_gives_no_item_to_the_benchmark_nor_to_an_asset_without_a_series_or_not_held():
    """Only a held asset with a prepared series is measured, and never the yardstick itself (D371).

    The benchmark is held: it gets no item — its beta on itself would be 1 by construction. Asset 4
    is held, but nothing prepared a series for it: no item, and no cost to the others. Asset 3 has a
    series, but is not held (another analytic's benchmark, prepared in the same request): no item.
    """
    context = holdings_context(scope_asset_ids=(2, HOLDING_BENCHMARK_ID, 4, 1))
    prepared_ids = {series.returns.asset_id for series in context.prepared_series.series}
    assert 4 not in prepared_ids
    assert {3, HOLDING_BENCHMARK_ID} <= prepared_ids

    output = compare_holdings(context).output

    assert [item.asset_id for item in output.items] == [1, 2]
    assert [item.beta for item in output.items] == pytest.approx([beta(HOLDING_RETURNS[asset_id], HOLDING_BENCHMARK) for asset_id in (1, 2)], rel=1e-12)


def test_comparison_of_a_single_asset_has_no_holding_items():
    """An asset scope is one series compared with the benchmark: its figures are the top-level ones, and `items` is empty."""
    context = make_context({1: HOLDING_RETURNS[1], HOLDING_BENCHMARK_ID: HOLDING_BENCHMARK}, scope_kind=RiskScopeKind.ASSET, scope_asset_ids=(1,))

    output = compare_holdings(context).output

    # The asset itself is measured, as before.
    assert output.beta == pytest.approx(beta(HOLDING_RETURNS[1], HOLDING_BENCHMARK), rel=1e-12)
    assert output.items == []


def test_a_flat_holding_has_a_zero_beta_and_no_correlation_and_is_named():
    """No variance, no covariance: its beta is a measured zero, while correlation divides by that variance.

    The warning is the per-asset one, naming the holding. The singular warnings stay with the
    portfolio's own figures, which are defined here, and the benchmark's ratios are defined too.
    """
    holdings = {**HOLDING_RETURNS, 3: [0.0015] * HOLDING_OBSERVATIONS}

    computation = compare_holdings(holdings_context(holdings))
    output = computation.output

    assert output.beta is not None
    assert output.correlation is not None
    items = {item.asset_id: item for item in output.items}
    assert sorted(items) == [1, 2, 3]
    assert items[3].correlation is None
    assert items[3].beta is not None
    assert items[3].beta == pytest.approx(0.0, abs=1e-12)
    assert None not in (items[1].correlation, items[2].correlation)
    assert [(warning.code, warning.message_i18n_key, warning.details.get("asset_ids")) for warning in computation.warnings] == [
        ("comparison_correlation_undefined", "risk.warnings.comparison_correlation_undefined_assets", [3]),
    ]


def test_a_flat_benchmark_leaves_every_holding_undefined_and_lets_the_singular_warnings_speak():
    """Against a series without variance nothing is defined, and saying so once per figure is enough.

    The two singular warnings already say that beta and correlation are undefined because the
    benchmark is flat; a per-asset warning listing every holding would say it again for each of them.
    The benchmark's own ratios follow their own rule: undefined, and named.
    """
    computation = compare_holdings(holdings_context(benchmark=[0.002] * HOLDING_OBSERVATIONS))
    output = computation.output

    # The portfolio's own figures, as before k6.
    assert (output.beta, output.correlation) == (None, None)
    assert [item.asset_id for item in output.items] == [1, 2, 3]
    assert all((item.beta, item.correlation) == (None, None) for item in output.items)
    assert (output.comparison_sharpe, output.comparison_sortino) == (None, None)
    warnings = {(warning.code, warning.message_i18n_key): warning for warning in computation.warnings}
    assert len(warnings) == len(computation.warnings)
    assert set(warnings) == {
        ("comparison_beta_undefined", "risk.warnings.comparison_beta_undefined"),
        ("comparison_correlation_undefined", "risk.warnings.comparison_correlation_undefined"),
        ("sharpe_undefined", "risk.warnings.sharpe_undefined_assets"),
        ("sortino_undefined", "risk.warnings.sortino_undefined_assets"),
    }
    for code in ("comparison_beta_undefined", "comparison_correlation_undefined"):
        assert "asset_ids" not in warnings[(code, f"risk.warnings.{code}")].details, code
    for code in ("sharpe_undefined", "sortino_undefined"):
        assert warnings[(code, f"risk.warnings.{code}_assets")].details["asset_ids"] == [HOLDING_BENCHMARK_ID], code


def test_comparison_names_the_benchmark_when_only_its_sortino_is_undefined():
    """A benchmark that moves but never loses has a Sharpe, and no downside for a Sortino to divide by."""
    gainer = [round(0.002 + 0.0015 * math.cos(index * 0.7), 10) for index in range(HOLDING_OBSERVATIONS)]
    context = make_context({1: HOLDING_RETURNS[1], HOLDING_BENCHMARK_ID: gainer}, scope_kind=RiskScopeKind.ASSET, scope_asset_ids=(1,))

    computation = compare_holdings(context)
    output = computation.output

    assert output.beta is not None
    assert output.comparison_sharpe == pytest.approx(annualized_sharpe(gainer, computation.annualization_factor), rel=1e-12)
    assert output.comparison_sortino is None
    assert [(warning.code, warning.message_i18n_key, warning.details.get("asset_ids")) for warning in computation.warnings] == [
        ("sortino_undefined", "risk.warnings.sortino_undefined_assets", [HOLDING_BENCHMARK_ID]),
    ]


def test_stress_projects_hypothetical_percentages_and_amounts():
    context = make_context(
        {1: [0.01] * 20, 2: [0.0] * 20},
        mode=RiskMode.CURRENT_COMPOSITION,
        asset_classifications={
            1: RiskAssetClassification(asset_class="STOCK"),
            2: RiskAssetClassification(asset_class="BOND"),
        },
    )
    computation = StressAnalytic().compute(
        StressParams(
            method=RiskStressMethod.HYPOTHETICAL,
            dimension=RiskScenarioDimension.ASSET_CLASS,
            bucket_shocks={"STOCK": -0.2, "BOND": 0.1},
        ),
        context,
    )
    output = computation.output

    assert output.portfolio_return == pytest.approx(-0.075)
    assert output.impact_amount == Decimal("-15.000")
    assert [impact.impact_amount for impact in output.impacts] == [
        Decimal("-20.0"),
        Decimal("5.0"),
    ]
    assert output.dimension == RiskScenarioDimension.ASSET_CLASS
    assert [item.bucket_id for item in output.configured_buckets] == [
        "BOND",
        "STOCK",
    ]
    assert output.impacts[0].bucket_audit[0].rule == RiskStressApplicationRule.DIRECT


def test_hypothetical_sector_uses_weighted_exposures_and_other_fallback():
    context = make_context(
        {1: [0.0] * 20, 2: [0.0] * 20},
        scope_kind=RiskScopeKind.ASSET_SET,
        mode=RiskMode.CURRENT_COMPOSITION,
        asset_classifications={
            1: RiskAssetClassification(
                asset_class="ETF",
                sector_exposures={
                    "Technology": 0.6,
                    "Financials": 0.4,
                },
            ),
            2: RiskAssetClassification(asset_class="ETF"),
        },
    )
    computation = StressAnalytic().compute(
        StressParams(
            method=RiskStressMethod.HYPOTHETICAL,
            dimension=RiskScenarioDimension.SECTOR,
            bucket_shocks={
                "Technology": -0.2,
                "Other": -0.1,
            },
        ),
        context,
    )

    assert [item.shock_return for item in computation.output.impacts] == pytest.approx([-0.16, -0.1])
    fallback = computation.output.impacts[1]
    assert fallback.metadata_fallback is True
    assert fallback.bucket_audit[0].rule == RiskStressApplicationRule.MISSING_METADATA_OTHER
    assert computation.warnings[0].degrades_result is False
    other = next(item for item in computation.output.configured_buckets if item.bucket_id == "Other")
    assert other.applied_asset_count == 2
    assert other.asset_exposure_total == pytest.approx(1.4)
    assert computation.output.classification_coverage == pytest.approx(0.5)


def test_hypothetical_geography_applies_country_before_eu_before_other():
    context = make_context(
        {1: [0.0] * 20},
        scope_kind=RiskScopeKind.ASSET_SET,
        scope_asset_ids=(1,),
        mode=RiskMode.CURRENT_COMPOSITION,
        asset_classifications={
            1: RiskAssetClassification(
                asset_class="ETF",
                geography_exposures={
                    "ITA": 0.5,
                    "DEU": 0.25,
                    "USA": 0.25,
                },
            )
        },
        geography_groups={
            "european_union": frozenset({"DEU", "ITA"}),
        },
    )
    computation = StressAnalytic().compute(
        StressParams(
            method=RiskStressMethod.HYPOTHETICAL,
            dimension=RiskScenarioDimension.GEOGRAPHY,
            bucket_shocks={
                "european_union": -0.2,
                "ITA": -0.3,
                "Other": 0,
            },
        ),
        context,
    )

    impact = computation.output.impacts[0]
    assert impact.shock_return == pytest.approx(-0.2)
    audit = {item.exposure_bucket_id: item for item in impact.bucket_audit}
    assert audit["ITA"].candidate_bucket_ids == [
        "ITA",
        "european_union",
        "Other",
    ]
    assert audit["ITA"].applied_bucket_id == "ITA"
    assert audit["ITA"].rule == RiskStressApplicationRule.COUNTRY
    assert audit["DEU"].applied_bucket_id == "european_union"
    assert audit["DEU"].rule == RiskStressApplicationRule.GEOGRAPHY_GROUP
    assert audit["USA"].applied_bucket_id == "Other"
    assert audit["USA"].rule == RiskStressApplicationRule.OTHER


def test_hypothetical_params_canonicalize_buckets_and_reject_legacy_contract():
    params = StressParams(
        method=RiskStressMethod.HYPOTHETICAL,
        dimension=RiskScenarioDimension.GEOGRAPHY,
        bucket_shocks={
            "other": 0,
            "ita": -0.3,
            "european_union": -0.2,
        },
    )
    assert params.bucket_shocks == {
        "ITA": -0.3,
        "Other": 0.0,
        "european_union": -0.2,
    }

    with pytest.raises(ValueError, match="Other bucket"):
        StressParams(
            method=RiskStressMethod.HYPOTHETICAL,
            dimension=RiskScenarioDimension.SECTOR,
            bucket_shocks={"Financials": -0.3},
        )
    with pytest.raises(ValueError, match="Extra inputs"):
        StressParams.model_validate(
            {
                "method": "hypothetical",
                "shocks": {"1": -0.2},
            }
        )


def test_historical_replay_uses_current_buy_and_hold_policy():
    context = make_context(
        {1: [0.1, 0.0] + [0.0] * 18, 2: [0.0, 0.1] + [0.0] * 18},
        mode=RiskMode.CURRENT_COMPOSITION,
    )
    replay_range = DateRangeModel(
        start=date(2026, 1, 2),
        end=date(2026, 1, 21),
    )
    computation = StressAnalytic().compute(
        StressParams(
            method=RiskStressMethod.HISTORICAL_REPLAY,
            replay_range=replay_range,
        ),
        context,
    )

    assert computation.output.portfolio_return == pytest.approx(0.075)
    assert computation.output.impact_amount == Decimal("15.000")
    assert computation.output.replay_range == replay_range
    assert computation.historical_replay_audit.proxy_count == 0
    assert computation.historical_replay_audit.excluded_count == 0
    assert [impact.return_source_asset_id for impact in computation.output.impacts] == [1, 2]


def test_historical_replay_proxy_replaces_only_the_return_series():
    returns = [0.1, -0.05] + [0.0] * 18
    replay_range = DateRangeModel(
        start=date(2026, 1, 2),
        end=date(2026, 1, 21),
    )
    direct = StressAnalytic().compute(
        StressParams(
            method=RiskStressMethod.HISTORICAL_REPLAY,
            replay_range=replay_range,
        ),
        make_context(
            {1: returns},
            scope_kind=RiskScopeKind.ASSET,
            mode=RiskMode.CURRENT_COMPOSITION,
            scope_asset_ids=(1,),
        ),
    )
    proxied = StressAnalytic().compute(
        StressParams(
            method=RiskStressMethod.HISTORICAL_REPLAY,
            replay_range=replay_range,
            proxy_assets=[{"asset_id": 1, "proxy_asset_id": 3}],
        ),
        make_context(
            {3: returns},
            scope_kind=RiskScopeKind.ASSET,
            mode=RiskMode.CURRENT_COMPOSITION,
            scope_asset_ids=(1,),
            primary_asset_id=3,
            replay_source_asset_ids={1: 3},
        ),
    )

    assert proxied.output.portfolio_return == pytest.approx(direct.output.portfolio_return)
    assert proxied.output.impacts[0].asset_id == 1
    assert proxied.output.impacts[0].return_source_asset_id == 3
    assert proxied.historical_replay_audit.proxy_assets[0].model_dump() == {
        "asset_id": 1,
        "proxy_asset_id": 3,
    }
    assert proxied.historical_replay_audit.proxy_series_usage == "returns_only"


def test_historical_replay_exclusion_preserves_zero_return_residual_weight():
    """Realigned to D376 (05/10/2026): the excluded asset leaves `impacts`, and nothing else moves.

    It used to pin `impacts == [1, 2]`, asset 2 drawn as a row at zero return, zero contribution
    and no money: the UI drew it as a +0.00% bar beside the assets that lived through the window,
    though it had no data in it. A zero is not an abstention (D151). So `output.impacts` holds the
    replayed assets alone, and the excluded one stays where it already was — the audit, with its
    weight, reason and treatment; `computation.excluded_assets`; the warnings. Its weight is still
    carried as cash at zero return: the figures are the ones this test pinned before.
    """
    replay_range = DateRangeModel(
        start=date(2026, 1, 2),
        end=date(2026, 1, 21),
    )
    computation = StressAnalytic().compute(
        StressParams(
            method=RiskStressMethod.HISTORICAL_REPLAY,
            replay_range=replay_range,
            excluded_assets=[2],
        ),
        make_context(
            {1: [0.1] + [0.0] * 19},
            mode=RiskMode.CURRENT_COMPOSITION,
            replay_source_asset_ids={1: 1},
            replay_excluded_asset_ids=(2,),
        ),
    )

    # Unchanged: half of the scope gains 10%, the excluded quarter sits at zero beside the cash
    # quarter, and the rest is not renormalized — 5%, ten euros of the two hundred.
    assert computation.output.portfolio_return == pytest.approx(0.05)
    assert computation.output.impact_amount == Decimal("10.000")
    # Only the replayed asset has a row; the excluded one is not a bar at zero.
    assert [impact.asset_id for impact in computation.output.impacts] == [1], "an excluded asset is still an impact row at zero return: impacts must carry the replayed assets only (D376)"
    (replayed,) = computation.output.impacts
    assert (replayed.weight, replayed.contribution_return) == (0.5, pytest.approx(0.05))
    # The excluded asset is where it already was, with its weight, its reason and its treatment.
    audit = computation.historical_replay_audit
    assert audit.excluded_weight_total == pytest.approx(0.25)
    assert [(item.asset_id, item.reason, item.weight, item.treatment) for item in audit.excluded_assets] == [
        (2, RiskHistoricalReplayExclusionReason.MANUAL_EXCLUSION, 0.25, RiskHistoricalReplayExclusionTreatment.ZERO_RETURN_RESIDUAL),
    ]
    assert computation.excluded_assets == (RiskExcludedAsset(asset_id=2, reason="manual_historical_replay_exclusion"),)
    assert [(warning.message_i18n_key, warning.details["asset_ids"], warning.details["treatment"]) for warning in computation.warnings] == [
        ("risk.warnings.historical_replay_excluded_manual", [2], "zero_return_residual"),
    ]


def test_historical_replay_auto_excludes_a_missing_original_instead_of_blocking():
    """Repaired to the contract of 24/09/2026; it used to pin the blocking raise.

    Formerly `test_historical_replay_requires_proxy_or_exclusion_for_missing_original`: an asset
    with no replay series and no proxy made the whole replay fail with "requires a manual proxy or
    explicit exclusion". The engine now excludes it on its own and replays the rest; only a scope
    with nothing left to replay is unavailable.
    """
    context = make_context(
        {1: [0.01] * 20},
        scope_kind=RiskScopeKind.ASSET_SET,
        mode=RiskMode.CURRENT_COMPOSITION,
        scope_asset_ids=(1, 2),
    )

    computation = StressAnalytic().compute(
        StressParams(
            method=RiskStressMethod.HISTORICAL_REPLAY,
            replay_range=context.requested_range,
        ),
        context,
    )

    # Asset 2 arrives without returns and no unusable reason says why: no prices in the window.
    assert [impact.asset_id for impact in computation.output.impacts] == [1]
    assert computation.output.impacts[0].shock_return == pytest.approx(1.01**20 - 1)
    assert [(item.asset_id, item.reason, item.weight, item.treatment) for item in computation.historical_replay_audit.excluded_assets] == [
        (2, RiskHistoricalReplayExclusionReason.NO_PRICES_IN_WINDOW, None, RiskHistoricalReplayExclusionTreatment.OMITTED_FROM_REPLAY),
    ]
    assert [(warning.code, warning.message_i18n_key, warning.details["asset_ids"]) for warning in computation.warnings] == [
        ("historical_replay_assets_excluded", "risk.warnings.historical_replay_excluded_no_prices", [2]),
    ]
    assert computation.excluded_assets == (RiskExcludedAsset(asset_id=2, reason="historical_replay_no_prices_in_window"),)

    # Alone in its scope, the same asset leaves nothing to replay — that, not a missing proxy, blocks.
    alone = make_context(
        {1: [0.01] * 20},
        scope_kind=RiskScopeKind.ASSET_SET,
        mode=RiskMode.CURRENT_COMPOSITION,
        scope_asset_ids=(2,),
    )
    with pytest.raises(RiskUnavailableError) as exc_info:
        StressAnalytic().compute(
            StressParams(
                method=RiskStressMethod.HISTORICAL_REPLAY,
                replay_range=alone.requested_range,
            ),
            alone,
        )

    assert exc_info.value.code == RiskErrorCode.INSUFFICIENT_HISTORY
    assert str(exc_info.value) == "No asset in the replay scope covers the replay window"
    # D372 (02/10/2026): the error also names the asset with its reason, weightless on an asset set.
    assert exc_info.value.details == {
        "excluded_asset_ids": [2],
        "excluded_assets": [{"asset_id": 2, "reason": "no_prices_in_window", "weight": None}],
    }


def test_historical_replay_rejects_existing_proxy_without_usable_series():
    context = make_context(
        {3: [0.01] * 20},
        scope_kind=RiskScopeKind.ASSET,
        mode=RiskMode.CURRENT_COMPOSITION,
        scope_asset_ids=(1,),
        primary_asset_id=3,
        replay_source_asset_ids={1: 3},
    )
    empty_prepared = PreparedAssetSeriesSet(
        requested_range=context.requested_range,
        target_currency="EUR",
        series=[
            PreparedAssetSeries(
                valuations=AssetValuationSeries(
                    asset_id=3,
                    target_currency="EUR",
                ),
                returns=AssetReturnSeries(
                    asset_id=3,
                    target_currency="EUR",
                ),
            )
        ],
        data_quality=DataQualityReport(
            unusable_assets=[
                DataQualityExcludedAsset(
                    asset_id=3,
                    reason=DataQualityExclusionReason.MISSING_FX,
                )
            ]
        ),
        fx_fingerprint="0" * 64,
    )
    context = replace(
        context,
        historical_replay=RiskHistoricalReplayContext(
            prepared_series=empty_prepared,
            source_asset_ids={1: 3},
            excluded_asset_ids=(),
            data_quality=empty_prepared.data_quality,
        ),
    )

    with pytest.raises(RiskUnavailableError) as exc_info:
        StressAnalytic().compute(
            StressParams(
                method=RiskStressMethod.HISTORICAL_REPLAY,
                replay_range=context.requested_range,
                proxy_assets=[{"asset_id": 1, "proxy_asset_id": 3}],
            ),
            context,
        )

    assert exc_info.value.code.value == "invalid_parameters"
    assert exc_info.value.details["reason"] == "missing_fx"


def test_historical_replay_asset_set_exclusion_is_omitted_not_zero_weighted():
    context = make_context(
        {1: [0.1] + [0.0] * 19},
        scope_kind=RiskScopeKind.ASSET_SET,
        mode=RiskMode.CURRENT_COMPOSITION,
        scope_asset_ids=(1, 2),
        replay_source_asset_ids={1: 1},
        replay_excluded_asset_ids=(2,),
    )
    computation = StressAnalytic().compute(
        StressParams(
            method=RiskStressMethod.HISTORICAL_REPLAY,
            replay_range=context.requested_range,
            excluded_assets=[2],
        ),
        context,
    )

    assert computation.output.portfolio_return is None
    assert [impact.asset_id for impact in computation.output.impacts] == [1]
    assert computation.historical_replay_audit.excluded_assets[0].treatment.value == "omitted_from_replay"


# Automatic replay exclusion (developer's decision of 24/09/2026). The service decides which assets
# do not cover the crisis window before it prepares the joint series, and hands the reasons over in
# `auto_excluded_assets`; an excluded asset therefore has no return source, exactly as below.

REPLAY_RANGE = DateRangeModel(start=date(2026, 1, 2), end=date(2026, 1, 21))
Reason = RiskHistoricalReplayExclusionReason
Treatment = RiskHistoricalReplayExclusionTreatment


def replay_context(
    returns_by_asset: dict[int, list[float]],
    *,
    scope_kind: RiskScopeKind,
    scope_asset_ids: tuple[int, ...],
    weights: dict[int, float] | None = None,
    cash_weight: float = 0.0,
    manual: tuple[int, ...] = (),
    auto: dict[int, RiskHistoricalReplayExclusionReason] | None = None,
    unusable: dict[int, DataQualityExclusionReason] | None = None,
    suggested: tuple[DateRangeModel, tuple[int, ...]] | None = None,
) -> RiskExecutionContext:
    """A replay context shaped the way the service builds it, with an optional verified proposal."""
    auto = dict(auto or {})
    context = make_context(
        returns_by_asset,
        scope_kind=scope_kind,
        mode=RiskMode.CURRENT_COMPOSITION,
        scope_asset_ids=scope_asset_ids,
    )
    return replace(
        context,
        weights=context.weights if weights is None else weights,
        cash_weight=context.cash_weight if weights is None else cash_weight,
        historical_replay=replace(
            context.historical_replay,
            source_asset_ids={asset_id: asset_id for asset_id in scope_asset_ids if asset_id not in manual and asset_id not in auto},
            excluded_asset_ids=tuple(sorted(manual)),
            data_quality=DataQualityReport(unusable_assets=[DataQualityExcludedAsset(asset_id=asset_id, reason=reason) for asset_id, reason in sorted((unusable or {}).items())]),
            auto_excluded_assets=auto,
            suggested_range=suggested[0] if suggested else None,
            suggested_range_recovers=suggested[1] if suggested else (),
        ),
    )


def replay(context: RiskExecutionContext, **params):
    return StressAnalytic().compute(
        StressParams(method=RiskStressMethod.HISTORICAL_REPLAY, replay_range=REPLAY_RANGE, **params),
        context,
    )


def test_historical_replay_auto_exclusion_keeps_the_weight_as_zero_return_cash():
    returns = {1: [0.1] + [0.0] * 19}
    common = {"scope_kind": RiskScopeKind.PORTFOLIO, "scope_asset_ids": (1, 2), "weights": {1: 0.5, 2: 0.25}, "cash_weight": 0.25}
    automatic = replay(replay_context(returns, **common, auto={2: Reason.STARTS_AFTER_WINDOW_START}))
    manual = replay(replay_context(returns, **common, manual=(2,)), excluded_assets=[2])

    # Half the scope gains 10%; the excluded quarter joins the cash quarter at zero return and the
    # rest is not renormalized: 5%, the same figure a manual exclusion gives.
    assert automatic.output.portfolio_return == pytest.approx(0.05)
    assert automatic.output.portfolio_return == pytest.approx(manual.output.portfolio_return)
    audit = automatic.historical_replay_audit
    assert audit.excluded_weight_total == pytest.approx(0.25)
    assert [(item.asset_id, item.reason, item.weight, item.treatment) for item in audit.excluded_assets] == [
        (2, Reason.STARTS_AFTER_WINDOW_START, 0.25, Treatment.ZERO_RETURN_RESIDUAL),
    ]
    impacts = {impact.asset_id: impact for impact in automatic.output.impacts}
    # D376 (05/10/2026): the excluded weight sits at zero beside the cash — the 5% above — but the
    # asset is no row of its own: drawn at zero return it read as "lived through the window and did
    # nothing", when it had no data in it at all (D151). The audit, the warning and the exclusions
    # below are where it is named. It used to pin {1, 2} and a (0.0, 0.0) row for asset 2.
    assert set(impacts) == {1}, "an automatically excluded asset is still an impact row at zero return (D376)"
    assert impacts[1].contribution_return == pytest.approx(0.05)
    # The manual exclusion of the same asset leaves the same single row.
    assert [impact.asset_id for impact in manual.output.impacts] == [1], "a manually excluded asset is still an impact row at zero return (D376)"
    (warning,) = automatic.warnings
    assert warning.code == "historical_replay_assets_excluded"
    assert warning.message_i18n_key == "risk.warnings.historical_replay_excluded_starts_late"
    assert warning.details == {"asset_ids": [2], "treatment": "zero_return_residual", "reason": "starts_after_window_start"}
    assert warning.message_params == {"treatment": "zero_return_residual"}
    assert automatic.excluded_assets == (RiskExcludedAsset(asset_id=2, reason="historical_replay_starts_after_window_start"),)

    # The manual exclusion keeps its own reason and sentence.
    assert manual.historical_replay_audit.excluded_assets[0].reason == Reason.MANUAL_EXCLUSION
    assert [warning.message_i18n_key for warning in manual.warnings] == ["risk.warnings.historical_replay_excluded_manual"]
    assert manual.excluded_assets == (RiskExcludedAsset(asset_id=2, reason="manual_historical_replay_exclusion"),)


def test_historical_replay_keeps_a_replayed_asset_that_came_out_flat_and_no_row_for_the_excluded_one():
    """D376 read with D151: who leaves `impacts` is decided by who was replayed, never by the value.

    Asset 1 lived through the window and ended exactly where it started: 0% is its figure, and its
    row stays. Asset 2 had no price in the window: it was never replayed, so it has no row, though
    its weight still counts as cash at zero return. Dropping the zero rows instead would get both
    of them wrong in one move — the flat asset gone, the excluded one gone for a reason that only
    happened to coincide.
    """
    computation = replay(
        replay_context(
            {1: [0.0] * 20},
            scope_kind=RiskScopeKind.PORTFOLIO,
            scope_asset_ids=(1, 2),
            weights={1: 0.5, 2: 0.25},
            cash_weight=0.25,
            auto={2: Reason.NO_PRICES_IN_WINDOW},
        )
    )

    assert computation.output.portfolio_return == 0.0
    assert [(impact.asset_id, impact.weight, impact.shock_return, impact.contribution_return) for impact in computation.output.impacts] == [(1, 0.5, 0.0, 0.0)], "the replayed asset that came out flat must keep its row, and the excluded one must have none (D376, D151)"
    assert [(item.asset_id, item.reason, item.weight, item.treatment) for item in computation.historical_replay_audit.excluded_assets] == [
        (2, Reason.NO_PRICES_IN_WINDOW, 0.25, Treatment.ZERO_RETURN_RESIDUAL),
    ]
    assert computation.historical_replay_audit.excluded_weight_total == pytest.approx(0.25)
    assert computation.excluded_assets == (RiskExcludedAsset(asset_id=2, reason="historical_replay_no_prices_in_window"),)


def test_historical_replay_auto_exclusion_omits_the_asset_from_an_asset_set():
    computation = replay(
        replay_context(
            {1: [0.1] + [0.0] * 19},
            scope_kind=RiskScopeKind.ASSET_SET,
            scope_asset_ids=(1, 2),
            auto={2: Reason.NO_PRICES_IN_WINDOW},
        )
    )

    assert computation.output.portfolio_return is None
    assert [impact.asset_id for impact in computation.output.impacts] == [1]
    assert computation.output.impacts[0].shock_return == pytest.approx(0.1)
    audit = computation.historical_replay_audit
    assert audit.excluded_weight_total == 0
    assert [(item.asset_id, item.reason, item.weight, item.treatment) for item in audit.excluded_assets] == [
        (2, Reason.NO_PRICES_IN_WINDOW, None, Treatment.OMITTED_FROM_REPLAY),
    ]
    (warning,) = computation.warnings
    assert warning.message_i18n_key == "risk.warnings.historical_replay_excluded_no_prices"
    assert warning.details == {"asset_ids": [2], "treatment": "omitted_from_replay", "reason": "no_prices_in_window"}
    assert warning.message_params == {"treatment": "omitted_from_replay"}


def test_historical_replay_audits_manual_and_automatic_exclusions_with_one_warning_per_reason():
    # Asset ids run against the enum on purpose, so the warnings' order can only be the enum's.
    weights = {1: 0.3, 2: 0.1, 3: 0.1, 4: 0.1, 5: 0.1, 6: 0.1, 7: 0.05, 8: 0.05}
    context = replay_context(
        {1: [0.1] + [0.0] * 19},
        scope_kind=RiskScopeKind.PORTFOLIO,
        scope_asset_ids=(1, 2, 3, 4, 5, 6, 7, 8),
        weights=weights,
        cash_weight=0.1,
        manual=(2,),
        auto={
            8: Reason.NO_PRICES_IN_WINDOW,
            7: Reason.NO_PRICES_IN_WINDOW,
            6: Reason.STARTS_AFTER_WINDOW_START,
            5: Reason.STALE_AT_WINDOW_START,
            4: Reason.STALE_AT_WINDOW_END,
            3: Reason.MISSING_FX,
        },
    )

    computation = replay(context, excluded_assets=[2])

    audit = computation.historical_replay_audit
    assert [(item.asset_id, item.reason) for item in audit.excluded_assets] == [
        (2, Reason.MANUAL_EXCLUSION),
        (3, Reason.MISSING_FX),
        (4, Reason.STALE_AT_WINDOW_END),
        (5, Reason.STALE_AT_WINDOW_START),
        (6, Reason.STARTS_AFTER_WINDOW_START),
        (7, Reason.NO_PRICES_IN_WINDOW),
        (8, Reason.NO_PRICES_IN_WINDOW),
    ]
    assert {item.treatment for item in audit.excluded_assets} == {Treatment.ZERO_RETURN_RESIDUAL}
    assert [item.weight for item in audit.excluded_assets] == [weights[asset_id] for asset_id in range(2, 9)]
    assert audit.excluded_count == len(audit.excluded_assets)
    assert audit.excluded_weight_total == pytest.approx(0.6)
    # The audit re-validates as it is: sorted, counted and weighed consistently.
    assert RiskHistoricalReplayAudit.model_validate(audit.model_dump()) == audit
    # Only asset 1 moves: 0.3 × 10%, everything excluded sits at zero next to the cash.
    assert computation.output.portfolio_return == pytest.approx(0.03)
    # …and only asset 1 is a row (D376): seven exclusions, one per reason the engine has, manual
    # included, and not one of them drawn as a bar at zero.
    assert [impact.asset_id for impact in computation.output.impacts] == [1], "an excluded asset is still an impact row at zero return (D376)"

    # Past half of the value excluded, the result first says it describes a minority of the
    # portfolio: 40% covered here, cash included, since cash is replayed at its zero return.
    mostly, *per_reason = computation.warnings
    assert (mostly.code, mostly.message_i18n_key, mostly.message_params) == ("historical_replay_mostly_excluded", "risk.warnings.historical_replay_mostly_excluded", {"covered": 0.4})
    assert mostly.details == {"excluded_weight_total": pytest.approx(0.6), "threshold": 0.5}

    # Then one warning per reason, never one per asset, in the enum's order, each with its own
    # sentence; only the two stale reasons say how many days, and it is the project's threshold.
    zero_cash = {"treatment": "zero_return_residual"}
    stale = {**zero_cash, "days": STALE_PRICE_THRESHOLD_DAYS}
    assert {warning.code for warning in per_reason} == {"historical_replay_assets_excluded"}
    assert [warning.details["reason"] for warning in per_reason] == [reason.value for reason in Reason]
    assert [(warning.message_i18n_key, warning.details["asset_ids"], warning.message_params) for warning in per_reason] == [
        ("risk.warnings.historical_replay_excluded_manual", [2], zero_cash),
        ("risk.warnings.historical_replay_excluded_no_prices", [7, 8], zero_cash),
        ("risk.warnings.historical_replay_excluded_starts_late", [6], zero_cash),
        ("risk.warnings.historical_replay_excluded_stale_at_start", [5], stale),
        ("risk.warnings.historical_replay_excluded_stale_at_end", [4], stale),
        ("risk.warnings.historical_replay_excluded_missing_fx", [3], zero_cash),
    ]
    assert [(item.asset_id, item.reason) for item in computation.excluded_assets] == [
        (2, "manual_historical_replay_exclusion"),
        (3, "historical_replay_missing_fx"),
        (4, "historical_replay_stale_at_window_end"),
        (5, "historical_replay_stale_at_window_start"),
        (6, "historical_replay_starts_after_window_start"),
        (7, "historical_replay_no_prices_in_window"),
        (8, "historical_replay_no_prices_in_window"),
    ]


@pytest.mark.parametrize(
    ("reason", "key"),
    [
        pytest.param(Reason.STALE_AT_WINDOW_START, "risk.warnings.historical_replay_excluded_stale_at_start", id="stale-at-start"),
        pytest.param(Reason.STALE_AT_WINDOW_END, "risk.warnings.historical_replay_excluded_stale_at_end", id="stale-at-end"),
    ],
)
def test_historical_replay_stale_exclusions_state_the_threshold_in_an_asset_set(reason, key):
    computation = replay(
        replay_context(
            {1: [0.1] + [0.0] * 19},
            scope_kind=RiskScopeKind.ASSET_SET,
            scope_asset_ids=(1, 2),
            auto={2: reason},
        )
    )

    (warning,) = computation.warnings
    assert warning.message_i18n_key == key
    assert warning.details == {"asset_ids": [2], "treatment": "omitted_from_replay", "reason": reason.value}
    assert warning.message_params == {"treatment": "omitted_from_replay", "days": STALE_PRICE_THRESHOLD_DAYS}
    assert computation.excluded_assets == (RiskExcludedAsset(asset_id=2, reason=f"historical_replay_{reason.value}"),)


def test_historical_replay_excludes_an_asset_arriving_without_returns_by_its_unusable_reason():
    computation = replay(
        replay_context(
            {1: [0.1] + [0.0] * 19},
            scope_kind=RiskScopeKind.ASSET_SET,
            scope_asset_ids=(1, 2, 3),
            unusable={
                2: DataQualityExclusionReason.MISSING_FX,
                3: DataQualityExclusionReason.MISSING_PRICE,
            },
        )
    )

    assert [(item.asset_id, item.reason) for item in computation.historical_replay_audit.excluded_assets] == [
        (2, Reason.MISSING_FX),
        (3, Reason.NO_PRICES_IN_WINDOW),
    ]
    assert [(warning.message_i18n_key, warning.details["asset_ids"]) for warning in computation.warnings] == [
        ("risk.warnings.historical_replay_excluded_no_prices", [3]),
        ("risk.warnings.historical_replay_excluded_missing_fx", [2]),
    ]


@pytest.mark.parametrize("scope_kind", [RiskScopeKind.PORTFOLIO, RiskScopeKind.ASSET_SET])
def test_historical_replay_with_nothing_left_to_replay_is_unavailable(scope_kind):
    # A portfolio whose assets are all excluded used to "replay" to a flat 0.0 of pure cash.
    context = replay_context(
        {1: [0.1] + [0.0] * 19},
        scope_kind=scope_kind,
        scope_asset_ids=(1, 2),
        weights={1: 0.5, 2: 0.25},
        cash_weight=0.25,
        manual=(1,),
        auto={2: Reason.STALE_AT_WINDOW_END},
    )

    with pytest.raises(RiskUnavailableError) as exc_info:
        replay(context, excluded_assets=[1])

    assert exc_info.value.code == RiskErrorCode.INSUFFICIENT_HISTORY
    assert str(exc_info.value) == "No asset in the replay scope covers the replay window"
    # D372 (02/10/2026): each excluded asset with its reason, and its weight where the scope has weights.
    weighted = scope_kind == RiskScopeKind.PORTFOLIO
    assert exc_info.value.details == {
        "excluded_asset_ids": [1, 2],
        "excluded_assets": [
            {"asset_id": 1, "reason": "manual_exclusion", "weight": 0.5 if weighted else None},
            {"asset_id": 2, "reason": "stale_at_window_end", "weight": 0.25 if weighted else None},
        ],
    }


# Nothing left to replay, read by the frontend (developer's decision D372 of 02/10/2026). With no
# replay there is no audit, so the error is the only place the replay block can read *why* each asset
# is out and how much of a weighted scope it held: `details["excluded_assets"]`, one item per excluded
# asset ordered by asset id, beside the `excluded_asset_ids` every reader already finds there.
#
# Asset ids run against the enum's order, so an answer ordered by reason cannot pass for one ordered
# by id; the weights are all different and follow neither, so one ordered by weight cannot either.
NOTHING_LEFT_REASONS = {
    1: Reason.MISSING_FX,
    2: Reason.STALE_AT_WINDOW_END,
    3: Reason.STALE_AT_WINDOW_START,
    4: Reason.STARTS_AFTER_WINDOW_START,
    5: Reason.NO_PRICES_IN_WINDOW,
    6: Reason.MANUAL_EXCLUSION,
}
NOTHING_LEFT_WEIGHTS = {1: 0.05, 2: 0.25, 3: 0.1, 4: 0.2, 5: 0.15, 6: 0.12}


@pytest.mark.parametrize(
    "scope_kind",
    [
        # B1: a weighted scope names each asset's weight, the very weight of the scope.
        pytest.param(RiskScopeKind.PORTFOLIO, id="portfolio-names-each-weight"),
        # B2: an asset set has no weights to name, whatever the context happens to hold.
        pytest.param(RiskScopeKind.ASSET_SET, id="asset-set-names-no-weight"),
    ],
)
def test_nothing_left_to_replay_names_each_excluded_asset_with_its_reason_and_weight(scope_kind):
    weighted = scope_kind == RiskScopeKind.PORTFOLIO
    context = replay_context(
        {1: [0.1] + [0.0] * 19},
        scope_kind=scope_kind,
        scope_asset_ids=tuple(NOTHING_LEFT_REASONS),
        # The same weights reach both scopes: the asset set must withhold them, not merely lack them.
        weights=NOTHING_LEFT_WEIGHTS,
        cash_weight=0.13,
        manual=(6,),
        auto={asset_id: reason for asset_id, reason in NOTHING_LEFT_REASONS.items() if reason != Reason.MANUAL_EXCLUSION},
    )

    with pytest.raises(RiskUnavailableError) as exc_info:
        replay(context, excluded_assets=[6])

    # The refusal itself is today's (24/09/2026), unchanged.
    assert exc_info.value.code == RiskErrorCode.INSUFFICIENT_HISTORY
    assert str(exc_info.value) == "No asset in the replay scope covers the replay window"
    details = exc_info.value.details
    assert details["excluded_asset_ids"] == [1, 2, 3, 4, 5, 6]

    # Every reason the engine has, each under its enum value — the string the API carries.
    expected = [{"asset_id": asset_id, "reason": NOTHING_LEFT_REASONS[asset_id].value, "weight": NOTHING_LEFT_WEIGHTS[asset_id] if weighted else None} for asset_id in sorted(NOTHING_LEFT_REASONS)]
    assert {item["reason"] for item in expected} == {reason.value for reason in Reason}
    assert details.get("excluded_assets") == expected, "the nothing-left error must name each excluded asset with its reason and weight (D372), ordered by asset id"
    # The error crosses the API as it stands: JSON, and nothing in it but what the reader is owed —
    # no proposal was found here, so none is offered.
    assert json.loads(json.dumps(details)) == details
    assert details == {"excluded_asset_ids": [1, 2, 3, 4, 5, 6], "excluded_assets": expected}


def test_historical_replay_unusable_proxy_stays_a_parameter_error_beside_automatic_exclusions():
    context = replay_context(
        {1: [0.1] + [0.0] * 19},
        scope_kind=RiskScopeKind.PORTFOLIO,
        scope_asset_ids=(1, 2),
        weights={1: 0.5, 2: 0.25},
        cash_weight=0.25,
        auto={2: Reason.STARTS_AFTER_WINDOW_START},
        unusable={3: DataQualityExclusionReason.MISSING_FX},
    )
    # Asset 1 replays through proxy 3, whose series is unusable.
    context = replace(context, historical_replay=replace(context.historical_replay, source_asset_ids={1: 3}))

    with pytest.raises(RiskUnavailableError) as exc_info:
        replay(context, proxy_assets=[{"asset_id": 1, "proxy_asset_id": 3}])

    # A proxy is the user's explicit choice: never swept into the automatic exclusions.
    assert exc_info.value.code == RiskErrorCode.INVALID_PARAMETERS
    assert exc_info.value.details == {"asset_id": 1, "return_source_asset_id": 3, "reason": "missing_fx"}


# The replay says so when most of the portfolio is excluded (developer's decision of 24/09/2026):
# the excluded share counts as idle cash, so past half of the value the loss replayed is the loss of
# a minority of the portfolio.


@pytest.mark.parametrize(
    ("weights", "expected_covered"),
    [
        pytest.param({1: 0.2, 2: 0.3, 3: 0.25}, 0.45, id="above-half-excluded"),
        pytest.param({1: 0.25, 2: 0.25, 3: 0.25}, None, id="exactly-half-excluded"),
        pytest.param({1: 0.35, 2: 0.2, 3: 0.2}, None, id="below-half-excluded"),
    ],
)
def test_historical_replay_warns_when_more_than_half_of_the_value_is_excluded(weights, expected_covered):
    computation = replay(
        replay_context(
            {1: [0.1] + [0.0] * 19},
            scope_kind=RiskScopeKind.PORTFOLIO,
            scope_asset_ids=(1, 2, 3),
            weights=weights,
            cash_weight=0.25,
            auto={2: Reason.STARTS_AFTER_WINDOW_START, 3: Reason.STALE_AT_WINDOW_END},
        )
    )

    excluded = weights[2] + weights[3]
    assert computation.historical_replay_audit.excluded_weight_total == pytest.approx(excluded)
    mostly = [warning for warning in computation.warnings if warning.code == "historical_replay_mostly_excluded"]
    if expected_covered is None:
        assert mostly == []
    else:
        (warning,) = mostly
        assert warning.message_i18n_key == "risk.warnings.historical_replay_mostly_excluded"
        assert warning.message_params == {"covered": expected_covered}
        assert warning.details == {"excluded_weight_total": pytest.approx(excluded), "threshold": 0.5}
        assert warning.message_params["covered"] == round(1 - excluded, 4)
    # The per-reason warnings are there either way.
    assert [warning.details["reason"] for warning in computation.warnings if warning.code == "historical_replay_assets_excluded"] == ["starts_after_window_start", "stale_at_window_end"]


def test_historical_replay_mostly_excluded_warning_follows_the_proxies_and_precedes_the_reasons():
    context = replay_context(
        {9: [0.1] + [0.0] * 19},
        scope_kind=RiskScopeKind.PORTFOLIO,
        scope_asset_ids=(1, 2, 3),
        weights={1: 0.2, 2: 0.3, 3: 0.25},
        cash_weight=0.25,
        auto={2: Reason.STARTS_AFTER_WINDOW_START, 3: Reason.STALE_AT_WINDOW_END},
    )
    # Asset 1 replays through proxy 9.
    context = replace(context, historical_replay=replace(context.historical_replay, source_asset_ids={1: 9}))

    computation = replay(context, proxy_assets=[{"asset_id": 1, "proxy_asset_id": 9}])

    assert [warning.code for warning in computation.warnings] == [
        "historical_replay_proxies_used",
        "historical_replay_mostly_excluded",
        "historical_replay_assets_excluded",
        "historical_replay_assets_excluded",
    ]


def test_historical_replay_of_an_asset_set_never_warns_about_the_excluded_weight():
    computation = replay(
        replay_context(
            {1: [0.1] + [0.0] * 19},
            scope_kind=RiskScopeKind.ASSET_SET,
            scope_asset_ids=(1, 2, 3),
            auto={2: Reason.STARTS_AFTER_WINDOW_START, 3: Reason.STALE_AT_WINDOW_END},
        )
    )

    # Two of three assets omitted, but an asset set has no weights to speak of.
    assert computation.historical_replay_audit.excluded_weight_total == 0
    assert "historical_replay_mostly_excluded" not in {warning.code for warning in computation.warnings}


# A replay proposal found and verified by the service reaches the result: in the audit when the
# replay runs, in the error when nothing is left to replay.

PROPOSED = DateRangeModel(start=date(2026, 1, 9), end=date(2026, 1, 21))


def test_historical_replay_audit_carries_the_verified_proposal_of_the_context():
    computation = replay(
        replay_context(
            {1: [0.1] + [0.0] * 19},
            scope_kind=RiskScopeKind.ASSET_SET,
            scope_asset_ids=(1, 2, 3),
            auto={3: Reason.STALE_AT_WINDOW_START, 2: Reason.STARTS_AFTER_WINDOW_START},
            suggested=(PROPOSED, (2, 3)),
        )
    )

    audit = computation.historical_replay_audit
    assert (audit.suggested_range, audit.suggested_range_recovers) == (PROPOSED, [2, 3])
    assert RiskHistoricalReplayAudit.model_validate(audit.model_dump()) == audit


def test_historical_replay_audit_has_no_proposal_when_the_context_has_none():
    audit = replay(replay_context({1: [0.1] + [0.0] * 19}, scope_kind=RiskScopeKind.ASSET_SET, scope_asset_ids=(1, 2), auto={2: Reason.STARTS_AFTER_WINDOW_START})).historical_replay_audit

    assert (audit.suggested_range, audit.suggested_range_recovers) == (None, [])


# Since D372 (02/10/2026) the error also names each excluded asset with its reason (weightless: an
# asset set), with or without a proposal.
NOTHING_LEFT_EXCLUDED = [
    {"asset_id": 1, "reason": "manual_exclusion", "weight": None},
    {"asset_id": 2, "reason": "starts_after_window_start", "weight": None},
]


@pytest.mark.parametrize(
    ("suggested", "expected_details"),
    [
        pytest.param(
            (PROPOSED, (2,)),
            {"excluded_asset_ids": [1, 2], "excluded_assets": NOTHING_LEFT_EXCLUDED, "suggested_range": {"start": "2026-01-09", "end": "2026-01-21"}, "suggested_range_recovers": [2]},
            id="with-a-verified-proposal",
        ),
        pytest.param(None, {"excluded_asset_ids": [1, 2], "excluded_assets": NOTHING_LEFT_EXCLUDED}, id="without-one"),
    ],
)
def test_nothing_left_to_replay_carries_the_proposal_in_the_error(suggested, expected_details):
    context = replay_context(
        {1: [0.1] + [0.0] * 19},
        scope_kind=RiskScopeKind.ASSET_SET,
        scope_asset_ids=(1, 2),
        manual=(1,),
        auto={2: Reason.STARTS_AFTER_WINDOW_START},
        suggested=suggested,
    )

    with pytest.raises(RiskUnavailableError) as exc_info:
        replay(context, excluded_assets=[1])

    assert exc_info.value.code == RiskErrorCode.INSUFFICIENT_HISTORY
    assert exc_info.value.details == expected_details


def test_historical_replay_params_are_canonical_and_disjoint():
    params = StressParams(
        method=RiskStressMethod.HISTORICAL_REPLAY,
        replay_range=DateRangeModel(
            start=date(2026, 1, 2),
            end=date(2026, 1, 21),
        ),
        proxy_assets=[
            {"asset_id": 4, "proxy_asset_id": 8},
            {"asset_id": 1, "proxy_asset_id": 7},
        ],
        excluded_assets=[6, 2],
    )

    assert [item.asset_id for item in params.proxy_assets] == [1, 4]
    assert params.excluded_assets == [2, 6]
    with pytest.raises(ValueError, match="both proxied and excluded"):
        StressParams(
            method=RiskStressMethod.HISTORICAL_REPLAY,
            replay_range=params.replay_range,
            proxy_assets=[{"asset_id": 1, "proxy_asset_id": 7}],
            excluded_assets=[1],
        )


def test_comparison_identity_and_historical_var_invariants():
    returns = [-0.02, 0.01, 0.0, 0.02, -0.01] * 4
    context = make_context(
        {1: returns, 2: returns},
        scope_kind=RiskScopeKind.ASSET,
        scope_asset_ids=(1,),
    )
    comparison = (
        ComparisonAnalytic()
        .compute(
            ComparisonParams(comparison_asset_id=2),
            context,
        )
        .output
    )

    assert comparison.active_return == pytest.approx(0)
    assert comparison.tracking_error == pytest.approx(0)
    assert comparison.information_ratio is None
    assert comparison.correlation == pytest.approx(1)
    assert comparison.beta == pytest.approx(1)

    tail = (
        HistoricalVarAnalytic()
        .compute(
            HistoricalVarParams(confidence_level=0.8),
            context,
        )
        .output
    )
    assert tail.conditional_value_at_risk >= tail.value_at_risk >= 0


@pytest.mark.asyncio
async def test_simulation_uses_current_composition_and_discloses_assumptions():
    driver = [0.01, -0.005, 0.002, -0.001] * 10
    context = make_context(
        {
            1: driver,
            2: [value * 0.5 for value in driver],
        },
        mode=RiskMode.CURRENT_COMPOSITION,
    )
    try:
        computation = await SimulationAnalytic().execute(
            SimulationParams(
                horizon_days=10,
                path_count=256,
                random_seed=123,
            ),
            context,
        )
    finally:
        await shutdown_quant_worker_pools()
    output = computation.output

    assert output.process.value == "gbm"
    assert output.sampling_method.value == "mc"
    assert output.path_count == 256
    assert output.aggregation_policy.value == "current_buy_and_hold"
    assert output.costs_included is False
    assert output.cash_flows_included is False
    assert output.rebalanced is False
    assert len(output.percentile_bands) == 11
    assert computation.n_observations == 40
    assert computation.random_seed == 123
    assert computation.sobol_start_index is None
    assert "quantlib" in computation.method
    assert PortfolioOptimizationAnalytic.output_kind.value == "optimization"


# ---------------------------------------------------------------------------
# VaR horizons in calendar days (developer's decision of 30/09/2026)
#
# `horizon_days` is calendar days. The analytic compounds n = max(1, round(horizon_days × f / 365))
# observations, f being the observed annualization factor of the series it reads: a month holds 21
# observations of a series quoted Monday to Friday and 30 of one quoted every day. The output states
# both, and the history floor is counted in the observations the horizon compounds.
# ---------------------------------------------------------------------------

VAR_RETURNS = [round(0.012 * math.sin(index * 0.7) - 0.004 * math.cos(index * 1.3), 10) for index in range(60)]
WEEKDAY_FACTOR = 365 * 5 / 7  # the observed factor of a series quoted Monday to Friday, ≈ 260.7


def var_context(returns: list[float], annualization_factor: float | None) -> RiskExecutionContext:
    """An asset scope reading `returns`, with the observed factor under test."""
    context = make_context({1: returns, 2: returns}, scope_kind=RiskScopeKind.ASSET, scope_asset_ids=(1,))
    return replace(context, annualization_factor=annualization_factor)


@pytest.mark.parametrize(
    ("annualization_factor", "horizon_days", "horizon_observations"),
    [
        pytest.param(252.0, 30, 21, id="a-month-of-a-252-a-year-series"),
        pytest.param(WEEKDAY_FACTOR, 30, 21, id="a-month-of-a-weekday-series"),
        pytest.param(252.0, 1, 1, id="a-day-is-never-less-than-one-observation"),
        pytest.param(365.0, 30, 30, id="a-month-of-a-series-quoted-every-day"),
    ],
)
def test_historical_var_compounds_the_observations_its_calendar_horizon_holds(annualization_factor, horizon_days, horizon_observations):
    output = HistoricalVarAnalytic().compute(HistoricalVarParams(confidence_level=0.95, horizon_days=horizon_days), var_context(VAR_RETURNS, annualization_factor)).output
    expected = historical_var_cvar(VAR_RETURNS, confidence_level=0.95, horizon_observations=horizon_observations)

    # The request's calendar horizon is echoed; the observations it holds are stated beside it.
    assert output.horizon_days == horizon_days
    assert output.horizon_observations == horizon_observations
    assert output.observations == len(VAR_RETURNS) - horizon_observations + 1
    assert output.value_at_risk == pytest.approx(expected.value_at_risk, rel=1e-12)
    assert output.conditional_value_at_risk == pytest.approx(expected.conditional_value_at_risk, rel=1e-12)


def test_historical_var_counts_its_history_floor_in_horizon_observations():
    # A month of a 252-a-year series is 21 observations: 40 returns leave 20 compounded windows,
    # exactly the floor, and 39 leave one fewer.
    enough = HistoricalVarAnalytic().compute(HistoricalVarParams(horizon_days=30), var_context(VAR_RETURNS[:40], 252.0)).output
    assert (enough.horizon_observations, enough.observations) == (21, HistoricalVarAnalytic.min_observations)

    with pytest.raises(RiskUnavailableError) as refused:
        HistoricalVarAnalytic().compute(HistoricalVarParams(horizon_days=30), var_context(VAR_RETURNS[:39], 252.0))

    assert refused.value.code == RiskErrorCode.INSUFFICIENT_HISTORY
    details = refused.value.details
    assert (details["horizon_days"], details["horizon_observations"], details["observations"], details["required"]) == (30, 21, 19, HistoricalVarAnalytic.min_observations)


def test_historical_var_without_an_observed_factor_refuses_as_the_annualized_metrics_do():
    context = var_context(VAR_RETURNS, None)
    with pytest.raises(RiskUnavailableError) as annualized:
        require_annualization_factor(context)

    # Without f there is no telling how many observations a calendar horizon holds.
    with pytest.raises(RiskUnavailableError) as refused:
        HistoricalVarAnalytic().compute(HistoricalVarParams(horizon_days=30), context)

    assert refused.value.code == annualized.value.code


def test_historical_var_missing_both_its_series_and_its_factor_names_the_series_first():
    context = replace(var_context(VAR_RETURNS, None), primary_returns=(), primary_return_dates=())

    with pytest.raises(RiskUnavailableError) as refused:
        HistoricalVarAnalytic().compute(HistoricalVarParams(horizon_days=30), context)

    assert refused.value.code == RiskErrorCode.DATA_UNAVAILABLE


def test_historical_var_calendar_horizon_is_a_new_algorithm_version():
    assert HistoricalVarAnalytic.algorithm_version == "3.0.0"


# ---------------------------------------------------------------------------
# Simulation steps (developer's decision of 30/09/2026): the block bootstrap resamples observations,
# so the plugin hands it the observed factor; GBM stays in calendar days. The drift's uncertainty,
# a sample mean compounded over the horizon, is compounded over the observations the horizon holds.
# ---------------------------------------------------------------------------

SIMULATION_DRIVER = [0.01, -0.005, 0.002, -0.001, 0.004, -0.007] * 7


def simulation_context(annualization_factor: float) -> RiskExecutionContext:
    context = make_context({1: SIMULATION_DRIVER, 2: [value * 0.5 for value in SIMULATION_DRIVER]}, mode=RiskMode.CURRENT_COMPOSITION)
    return replace(context, annualization_factor=annualization_factor)


def bootstrap_params(horizon_days: int) -> SimulationParams:
    return SimulationParams(horizon_days=horizon_days, path_count=256, bootstrap_seed=7)


def gbm_params(horizon_days: int) -> SimulationParams:
    return SimulationParams(horizon_days=horizon_days, path_count=256, random_seed=7)


@pytest.fixture
def engine_requests(monkeypatch) -> list:
    """Answer every engine call with a flat result, and keep the request it was given."""
    captured: list = []

    async def fake_run_simulation(request, *, algorithm_version):
        captured.append(request)
        flat = [0.0] * (request.horizon_days + 1)
        assets = len(request.asset_ids)
        result = SimulationEngineResult(
            percentile_paths=[flat, flat, flat],
            terminal_mean_return=0.0,
            terminal_volatility=0.0,
            probability_of_loss=0.0,
            terminal_asset_log_means=[0.0] * assets,
            terminal_asset_log_covariance=[[0.0] * assets for _ in range(assets)],
            # A resample always discloses its block; a parametric result never has one.
            block_length_days=4 if request.process == RiskSimulationProcess.BLOCK_BOOTSTRAP else None,
        )
        return result, False, None

    monkeypatch.setattr(simulation_plugin_module, "run_simulation", fake_run_simulation)
    return captured


@pytest.mark.asyncio
async def test_simulation_hands_the_observed_factor_to_the_bootstrap_and_not_to_gbm(engine_requests):
    context = simulation_context(252.0)

    await SimulationAnalytic().execute(bootstrap_params(30), context)
    await SimulationAnalytic().execute(gbm_params(30), context)

    bootstrap, gbm = engine_requests
    assert bootstrap.process == RiskSimulationProcess.BLOCK_BOOTSTRAP
    assert bootstrap.steps_per_year == 252.0
    # The horizon still travels in calendar days: the engine converts it.
    assert bootstrap.horizon_days == 30
    assert gbm.process == RiskSimulationProcess.GBM
    assert gbm.steps_per_year is None
    assert gbm.horizon_days == 30


@pytest.mark.parametrize("params", [pytest.param(bootstrap_params, id="block-bootstrap"), pytest.param(gbm_params, id="gbm")])
@pytest.mark.asyncio
async def test_drift_uncertainty_compounds_over_the_observations_the_horizon_holds(engine_requests, params):
    context = simulation_context(252.0)

    output = (await SimulationAnalytic().execute(params(365), context)).output

    returns = {1: SIMULATION_DRIVER, 2: [value * 0.5 for value in SIMULATION_DRIVER]}
    weights = [context.weights[1], context.weights[2]]
    # A year of a 252-a-year series is 252 observations, not 365.
    expected, observations = estimate_drift_uncertainty(returns, (1, 2), weights, horizon_observations=252)
    over_calendar_days, _ = estimate_drift_uncertainty(returns, (1, 2), weights, horizon_observations=365)
    assert output.drift_uncertainty_factor == pytest.approx(expected, rel=1e-12)
    assert output.drift_uncertainty_factor != pytest.approx(over_calendar_days, rel=1e-6)
    assert output.drift_uncertainty_observations == observations
    # The bands are still one per calendar day.
    assert len(output.percentile_bands) == 366


def test_simulation_steps_are_a_new_algorithm_version():
    assert SimulationAnalytic.algorithm_version == "4.0.0-bootstrap-quantlib-1.43"


@pytest.mark.asyncio
async def test_the_plugin_compares_a_block_with_the_history_in_observations(engine_requests):
    driver = SIMULATION_DRIVER[:30]
    context = replace(make_context({1: driver, 2: [value * 0.5 for value in driver]}, mode=RiskMode.CURRENT_COMPOSITION), annualization_factor=252.0)

    # 40 calendar days of a 252-a-year series are 28 observations: they fit in 30, and the engine
    # receives the block in calendar days, to convert it the same way.
    await SimulationAnalytic().execute(SimulationParams(horizon_days=30, path_count=256, bootstrap_seed=7, block_length_days=40), context)
    (request,) = engine_requests
    assert request.block_length_days == 40

    # 50 days are 35 observations: still refused as the user's choice, naming both units.
    with pytest.raises(RiskUnavailableError) as refused:
        await SimulationAnalytic().execute(SimulationParams(horizon_days=30, path_count=256, bootstrap_seed=7, block_length_days=50), context)

    assert refused.value.code == RiskErrorCode.INVALID_PARAMETERS
    details = refused.value.details
    assert (details["block_length_days"], details["block_length_observations"], details["observations"]) == (50, 35, 30)
    assert len(engine_requests) == 1


# ---------------------------------------------------------------------------
# Size limits (developer's decision D379, 07/10/2026): a simulation too large to run is a
# RESOURCE_LIMIT -- never INVALID_PARAMETERS nor EXECUTION_FAILED -- and its details name the
# limit that was hit and the remedy that actually works. `remedy` is a wire contract with the
# frontend, which turns it into a sentence, so its literal values are asserted here.
#
# `MAX_SIMULATION_ASSETS` is read inside the test bodies, never imported at the top: the constant
# is part of the contract under test, and a missing name must fail only the tests that use it.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("metric", "actual", "limit", "remedy"),
    [
        pytest.param("portfolio_cells", MAX_PORTFOLIO_CELLS + 1, MAX_PORTFOLIO_CELLS, "paths_or_horizon", id="portfolio-cells"),
        pytest.param("stochastic_cells", MAX_STOCHASTIC_CELLS + 1, MAX_STOCHASTIC_CELLS, "paths_or_horizon", id="stochastic-cells"),
        pytest.param("history_cells", MAX_HISTORY_CELLS + 1, MAX_HISTORY_CELLS, "period", id="history-cells"),
        # A budget the plugin has never heard of is still "too large", only without a remedy
        # it cannot vouch for: the frontend falls back to its generic sentence.
        pytest.param("future_metric", 11, 10, None, id="unknown-metric-without-remedy"),
    ],
)
@pytest.mark.asyncio
async def test_an_engine_budget_refusal_is_a_resource_limit_with_the_remedy_that_works(monkeypatch, metric, actual, limit, remedy):
    # Until D379 every budget refusal became INVALID_PARAMETERS: the user read "Invalid calculation
    # parameters" even at the defaults, about parameters nothing was wrong with.
    async def over_budget(request, *, algorithm_version):
        raise SimulationResourceLimitError("over the budget", metric=metric, actual=actual, limit=limit)

    monkeypatch.setattr(simulation_plugin_module, "run_simulation", over_budget)

    with pytest.raises(RiskUnavailableError) as refused:
        await SimulationAnalytic().execute(bootstrap_params(30), simulation_context(252.0))

    expected = {"metric": metric, "actual": actual, "limit": limit}
    if remedy is not None:
        expected["remedy"] = remedy
    assert refused.value.code == RiskErrorCode.RESOURCE_LIMIT
    assert refused.value.details == expected


@pytest.fixture
def budgeted_engine_requests(engine_requests, monkeypatch) -> list:
    """`engine_requests` behind the engine's REAL resource budget, still without a worker.

    The production `run_simulation` checks the budget before it reads the cache or spawns
    anything, so running that same check and then the flat fake gives the verdict a user
    would get -- refused or answered -- for the price of three multiplications. A refused
    request is never captured: the list holds only what the engine would have run.
    """
    flat_engine = simulation_plugin_module.run_simulation

    async def budgeted_run_simulation(request, *, algorithm_version):
        validate_resource_budget(request)
        return await flat_engine(request, algorithm_version=algorithm_version)

    monkeypatch.setattr(simulation_plugin_module, "run_simulation", budgeted_run_simulation)
    return engine_requests


def positions_context(count: int) -> RiskExecutionContext:
    """A current-composition portfolio of `count` equally weighted positions, fully invested, on the short driver."""
    asset_ids = tuple(range(1, count + 1))
    context = make_context(dict.fromkeys(asset_ids, SIMULATION_DRIVER), mode=RiskMode.CURRENT_COMPOSITION, scope_asset_ids=asset_ids)
    return replace(context, weights=dict.fromkeys(asset_ids, 1.0 / count), cash_weight=0.0)


@pytest.mark.asyncio
async def test_at_the_defaults_the_first_position_over_the_compute_budget_is_a_resource_limit(budgeted_engine_requests):
    defaults = SimulationParams()
    largest = MAX_STOCHASTIC_CELLS // (defaults.path_count * defaults.horizon_days)
    # The user-visible threshold A measured on 07/10/2026 at the defaults (block bootstrap,
    # 365 days, 8192 paths), and the one the changelog cites: a change here must be
    # deliberate, never the side effect of moving a default or a budget.
    assert largest == 66

    # The first position too many, through the real budget. Before D379 this read "Invalid
    # calculation parameters", at parameters the user had never touched.
    with pytest.raises(RiskUnavailableError) as refused:
        await SimulationAnalytic().execute(defaults, positions_context(largest + 1))

    assert refused.value.code == RiskErrorCode.RESOURCE_LIMIT
    assert refused.value.details == {
        "metric": "stochastic_cells",
        "actual": defaults.path_count * defaults.horizon_days * (largest + 1),
        "limit": MAX_STOCHASTIC_CELLS,
        "remedy": "paths_or_horizon",
    }
    assert budgeted_engine_requests == []

    # CONTROL -- one position fewer, the defaults untouched, runs.
    await SimulationAnalytic().execute(defaults, positions_context(largest))
    (request,) = budgeted_engine_requests
    assert len(request.asset_ids) == largest


@pytest.mark.parametrize("params", [pytest.param(bootstrap_params, id="block-bootstrap"), pytest.param(gbm_params, id="gbm")])
@pytest.mark.asyncio
async def test_more_positions_than_the_engine_carries_are_a_resource_limit_that_never_reaches_it(engine_requests, params):
    limit = simulation_models.MAX_SIMULATION_ASSETS
    over = limit + 1

    # Before D379 the request for these positions failed its own validation outside the
    # plugin's `try`: a pydantic ValidationError escaped `execute`, which is exactly what made
    # the service log a traceback and answer EXECUTION_FAILED -- "we failed", for a portfolio
    # that is only too big. A RiskUnavailableError is reported as unavailable, with its code.
    with pytest.raises(RiskUnavailableError) as refused:
        await SimulationAnalytic().execute(params(30), positions_context(over))

    assert refused.value.code == RiskErrorCode.RESOURCE_LIMIT
    assert refused.value.details == {"metric": "assets", "actual": over, "limit": limit, "remedy": "positions"}
    # Refused before any request exists, so the engine never sees it.
    assert engine_requests == []

    # CONTROL -- one position fewer, same process and parameters, reaches the engine.
    await SimulationAnalytic().execute(params(30), positions_context(limit))
    (request,) = engine_requests
    assert len(request.asset_ids) == limit


@pytest.mark.asyncio
async def test_portfolio_optimization_executes_for_supported_scopes():
    clear_optimization_cache()
    returns_by_asset = {
        1: [0.001 + 0.01 * math.sin(index / 4) for index in range(60)],
        2: [0.0005 + 0.007 * math.cos(index / 5) for index in range(60)],
    }
    outputs = []
    try:
        for scope_kind in (
            RiskScopeKind.PORTFOLIO,
            RiskScopeKind.ASSET_SET,
        ):
            computation = await PortfolioOptimizationAnalytic().execute(
                PortfolioOptimizationParams(),
                make_context(
                    returns_by_asset,
                    scope_kind=scope_kind,
                ),
            )
            outputs.append(computation.output)
    finally:
        await shutdown_quant_worker_pools()

    assert all(sum(item.weight for item in output.weights) == pytest.approx(1.0, abs=1e-6) for output in outputs)


# ---------------------------------------------------------------------------
# Acquired measures: worst realization and the drawdown family.
#
# The expected values below were produced by riskfolio-lib 7.0.1 on the series
# built by ``_oracle_returns`` and are pinned as literals. Pinning rather than
# calling the library keeps the oracle meaningful: if a future version of
# riskfolio changes a definition, these tests state what the product promised,
# instead of silently agreeing with the new behaviour.
#
# riskfolio returns positive magnitudes; ``RiskKpiOutput`` states losses as
# negatives. Every comparison below therefore negates, except the ulcer index,
# which is a dispersion and non-negative in both conventions.
# ---------------------------------------------------------------------------

RISKFOLIO_WR = 0.0230038964
RISKFOLIO_MDD_REL = 0.6457267132036301
RISKFOLIO_DAR_REL = 0.6272197808285761
RISKFOLIO_CDAR_REL = 0.6333273658064632
RISKFOLIO_UCI_REL = 0.4190087283464846

# 1 unit in the last place. The product and the library accumulate the same
# products in a different order, so the agreement is to floating-point noise and
# never to the bit. See ``test_max_drawdown_equals_relative_mdd_but_not_bitwise``.
ORACLE_TOLERANCE = 1e-12


def _oracle_returns() -> list[float]:
    """Deterministic series with one long, deep drawdown between day 250 and 520.

    Arithmetic rather than seeded-random on purpose: ``random.gauss`` is stable
    today but is an implementation detail of CPython, while sine and cosine are
    not going to move.
    """
    values = []
    for index in range(750):
        wave = 0.012 * math.sin(index * 0.7) + 0.008 * math.cos(index * 0.23)
        drift = 0.0006 if index < 250 or index > 520 else -0.0035
        values.append(round(wave + drift, 10))
    return values


def _oracle_drawdowns() -> list[float]:
    return list(summarize_drawdown(_oracle_returns()).drawdowns)


def test_acquired_measures_match_the_riskfolio_oracle():
    returns = _oracle_returns()
    drawdowns = _oracle_drawdowns()

    assert acquired.worst_realization(returns) == pytest.approx(-RISKFOLIO_WR, abs=ORACLE_TOLERANCE)
    assert acquired.maximum_drawdown(drawdowns) == pytest.approx(-RISKFOLIO_MDD_REL, abs=ORACLE_TOLERANCE)
    assert acquired.drawdown_at_risk(drawdowns) == pytest.approx(-RISKFOLIO_DAR_REL, abs=ORACLE_TOLERANCE)
    assert acquired.conditional_drawdown_at_risk(drawdowns) == pytest.approx(-RISKFOLIO_CDAR_REL, abs=ORACLE_TOLERANCE)
    assert acquired.ulcer_index(drawdowns) == pytest.approx(RISKFOLIO_UCI_REL, abs=ORACLE_TOLERANCE)


def test_acquired_measures_carry_the_documented_sign_one_field_at_a_time():
    """One assertion per field, so a half-applied sign flip cannot hide.

    A single aggregate assertion would let two opposite conventions coexist
    inside one output as long as they cancelled.
    """
    returns = _oracle_returns()
    drawdowns = _oracle_drawdowns()

    assert acquired.worst_realization(returns) < 0
    assert acquired.maximum_drawdown(drawdowns) < 0
    assert acquired.drawdown_at_risk(drawdowns) < 0
    assert acquired.conditional_drawdown_at_risk(drawdowns) < 0
    assert acquired.ulcer_index(drawdowns) > 0


def test_conditional_drawdown_is_never_shallower_than_the_quantile():
    drawdowns = _oracle_drawdowns()
    assert acquired.conditional_drawdown_at_risk(drawdowns) <= acquired.drawdown_at_risk(drawdowns)
    assert acquired.maximum_drawdown(drawdowns) <= acquired.conditional_drawdown_at_risk(drawdowns)


def test_conditional_drawdown_is_not_the_mean_of_the_worst_tail():
    """Guards the exact defect this subsystem is being corrected for.

    riskfolio normalizes the tail integral by ``alpha * T``, not by the number of
    observations in the tail. The arithmetic mean is close enough to look right
    and wrong enough to matter, so this test pins the gap rather than the value.
    """
    drawdowns = _oracle_drawdowns()
    tail = sorted(drawdowns[1:])
    index = math.ceil(0.05 * len(tail)) - 1
    naive_mean = sum(tail[: index + 1]) / (index + 1)

    computed = acquired.conditional_drawdown_at_risk(drawdowns)

    assert computed != pytest.approx(naive_mean, abs=1e-9)
    assert computed < naive_mean


def test_drawdown_quantiles_exclude_the_baseline_point():
    """The baseline must not be counted, even when the quantile does not move.

    On most series the inserted zero sorts away from the quantile and DaR is
    unchanged, which is precisely why this is asserted on the conditional
    measure: its ``alpha * T`` denominator shifts whether or not the quantile
    does. A passing DaR proves nothing here.
    """
    drawdowns = _oracle_drawdowns()
    returns = _oracle_returns()

    assert len(drawdowns) == len(returns) + 1
    assert drawdowns[0] == 0.0

    with_baseline_denominator = len(drawdowns)
    without_baseline_denominator = len(drawdowns) - 1
    assert with_baseline_denominator != without_baseline_denominator

    tail = sorted(drawdowns[1:])
    index = math.ceil(0.05 * len(tail)) - 1
    quantile = tail[index]
    excess = math.fsum(tail[position] - quantile for position in range(index + 1))
    wrong = quantile + excess / (0.05 * len(drawdowns))

    assert acquired.conditional_drawdown_at_risk(drawdowns) != pytest.approx(wrong, abs=1e-12)


def test_ulcer_index_divides_by_the_number_of_returns_not_by_one_less():
    """``n - 1`` in riskfolio removes the inserted baseline; it is not Bessel."""
    drawdowns = _oracle_drawdowns()
    bessel = math.sqrt(math.fsum(value * value for value in drawdowns) / (len(drawdowns) - 2))

    computed = acquired.ulcer_index(drawdowns)

    assert computed == pytest.approx(RISKFOLIO_UCI_REL, abs=ORACLE_TOLERANCE)
    assert computed != pytest.approx(bessel, abs=1e-9)


def test_acquired_drawdowns_are_peak_relative_not_absolute():
    """Pins ``_Rel`` against ``_Abs``, which differ by more than a rounding."""
    drawdowns = _oracle_drawdowns()

    assert acquired.maximum_drawdown(drawdowns) == pytest.approx(-RISKFOLIO_MDD_REL, abs=ORACLE_TOLERANCE)
    assert abs(acquired.maximum_drawdown(drawdowns)) < 1.0
    assert acquired.ulcer_index(drawdowns) == pytest.approx(RISKFOLIO_UCI_REL, abs=ORACLE_TOLERANCE)


def test_max_drawdown_equals_relative_mdd_but_not_bitwise():
    """``summarize_drawdown`` already produces MDD_Rel, to floating-point noise.

    The agreement is structural: both build a compounded wealth index and take
    ``(peak - value) / peak``. It is not bit-exact, because the two
    implementations accumulate the same products in a different order. Any
    assertion written as ``==`` against the library would fail on a difference
    of one unit in the last place, which is why the product must not grow a
    second field restating the same quantity.
    """
    summary = summarize_drawdown(_oracle_returns())

    assert summary.max_drawdown == pytest.approx(-RISKFOLIO_MDD_REL, abs=ORACLE_TOLERANCE)
    assert summary.max_drawdown == pytest.approx(acquired.maximum_drawdown(list(summary.drawdowns)), abs=ORACLE_TOLERANCE)


def test_worst_realization_reports_the_day_it_happened():
    returns = _oracle_returns()
    index = acquired.worst_realization_index(returns)

    assert returns[index] == acquired.worst_realization(returns)
    assert returns[index] == min(returns)


def test_worst_realization_resolves_ties_to_the_earliest_day():
    returns = [0.01, -0.04, 0.02, -0.04, 0.03]
    assert acquired.worst_realization_index(returns) == 1


def test_worst_realization_is_not_floored_when_every_day_gained():
    """A window without a losing day has a positive worst realization.

    Flooring it at zero would pair 'you lost nothing' with a date pointing at a
    profitable day. The pure measure tells the truth; adapting the degenerate
    case to the ``le=0`` contract belongs to the plugin.
    """
    returns = [0.004, 0.001, 0.007, 0.002]
    assert acquired.worst_realization(returns) == pytest.approx(0.001)


def test_effective_number_of_assets_is_the_inverse_herfindahl():
    weights = [0.5, 0.3, 0.15, 0.05]
    computed = acquired.effective_number_of_assets(weights)

    assert computed == pytest.approx(2.73972602739726, abs=1e-12)
    assert computed == pytest.approx(1.0 / sum(weight**2 for weight in weights), abs=1e-12)

    herfindahl_points = sum((weight * 100) ** 2 for weight in weights)
    assert computed == pytest.approx(10000.0 / herfindahl_points, abs=1e-12)


def test_effective_number_of_assets_counts_positions_not_percentages():
    """Equal weights must return the position count itself, in units of positions."""
    for count in (1, 4, 10, 37):
        weights = [1.0 / count] * count
        assert acquired.effective_number_of_assets(weights) == pytest.approx(count, abs=1e-9)


def test_effective_number_of_assets_keeps_cash_in_the_denominator():
    """Weights that do not sum to one are consumed as given.

    Risk weights are ``position value / net worth``, the same denominator AI
    Export uses. Renormalizing here would make the product state two different
    concentrations for one portfolio.
    """
    invested = [0.25, 0.25]
    assert acquired.effective_number_of_assets(invested) == pytest.approx(8.0, abs=1e-9)

    renormalized = [0.5, 0.5]
    assert acquired.effective_number_of_assets(renormalized) == pytest.approx(2.0, abs=1e-9)


def test_effective_number_of_assets_is_none_for_a_fully_liquid_scope():
    assert acquired.effective_number_of_assets([0.0, 0.0]) is None


def test_diversification_ratio_sees_the_correlation_that_asset_count_cannot():
    """The reason the two measures must be published together.

    Ten equally weighted assets score ten on the effective count whether they
    are independent or move as one. Only the ratio distinguishes them.
    """
    size = 10
    volatility = 0.2
    weights = [1.0 / size] * size
    ratios = []

    for correlation in (0.0, 0.5, 0.95):
        covariance = [[volatility * volatility * (1.0 if row == column else correlation) for column in range(size)] for row in range(size)]
        variance = math.fsum(weights[row] * covariance[row][column] * weights[column] for row in range(size) for column in range(size))
        portfolio_volatility = math.sqrt(variance)

        assert acquired.effective_number_of_assets(weights) == pytest.approx(size, abs=1e-9)
        ratios.append(acquired.diversification_ratio(covariance, weights, portfolio_volatility=portfolio_volatility))

    assert ratios[0] == pytest.approx(math.sqrt(size), abs=1e-9)
    assert ratios[0] > ratios[1] > ratios[2]
    assert ratios[2] == pytest.approx(1.0, abs=0.05)


def test_diversification_ratio_is_one_for_a_single_holding():
    assert acquired.diversification_ratio([[0.04]], [1.0], portfolio_volatility=0.2) == pytest.approx(1.0, abs=1e-12)


def test_diversification_ratio_is_invariant_to_scale_and_annualization():
    """The only acquired measure comparable across portfolios holding different cash."""
    covariance = [[0.04, 0.006], [0.006, 0.09]]
    weights = [0.6, 0.4]
    variance = math.fsum(weights[row] * covariance[row][column] * weights[column] for row in range(2) for column in range(2))
    baseline = acquired.diversification_ratio(covariance, weights, portfolio_volatility=math.sqrt(variance))

    scaled_weights = [weight * 0.25 for weight in weights]
    scaled_volatility = math.sqrt(variance) * 0.25
    assert acquired.diversification_ratio(covariance, scaled_weights, portfolio_volatility=scaled_volatility) == pytest.approx(baseline, abs=1e-12)

    factor = 252.0
    annualized = [[value * factor for value in row] for row in covariance]
    assert acquired.diversification_ratio(annualized, weights, portfolio_volatility=math.sqrt(variance * factor)) == pytest.approx(baseline, abs=1e-12)


def test_diversification_ratio_is_never_below_one_for_long_only_weights():
    covariance = [[0.04, -0.01, 0.002], [-0.01, 0.09, 0.004], [0.002, 0.004, 0.0225]]
    weights = [0.5, 0.3, 0.2]
    variance = math.fsum(weights[row] * covariance[row][column] * weights[column] for row in range(3) for column in range(3))

    assert acquired.diversification_ratio(covariance, weights, portfolio_volatility=math.sqrt(variance)) >= 1.0


def test_diversification_ratio_is_none_without_portfolio_volatility():
    assert acquired.diversification_ratio([[0.0]], [1.0], portfolio_volatility=0.0) is None


def test_acquired_measures_reject_malformed_input():
    with pytest.raises(ValueError):
        acquired.worst_realization([])
    with pytest.raises(ValueError):
        acquired.ulcer_index([0.0])
    with pytest.raises(ValueError):
        acquired.drawdown_at_risk([0.0, -0.1], confidence_level=1.0)
    with pytest.raises(ValueError):
        acquired.effective_number_of_assets([0.5, -0.2])
    with pytest.raises(ValueError):
        acquired.diversification_ratio([[0.04]], [0.5, 0.5], portfolio_volatility=0.2)


# ---------------------------------------------------------------------------
# Plugin wiring for the acquired measures.
#
# The section above pins the mathematics. These pin the *plugins*: that every
# field is populated at all, that the parameter actually reaches the measure,
# that a window without a losing day is adapted to the ``le=0`` contract instead
# of floored, and that ``risk_contribution`` consumes the weights it is handed.
# ---------------------------------------------------------------------------


def _kpi_returns() -> list[float]:
    """24 observations whose single worst day sits at index 7 — at neither end.

    A minimum parked on the first or the last observation is satisfied by an
    off-by-one in one direction or the other, so it would say nothing about the
    date the plugin publishes.
    """
    values = [round(0.004 * math.sin(index * 0.9) + 0.001, 10) for index in range(24)]
    values[7] = -0.045
    return values


def _all_positive_returns() -> list[float]:
    """A window with no losing day, at more than ``min_observations`` length."""
    return [round(0.0008 + 0.0004 * (index % 5), 10) for index in range(24)]


def _contribution_returns() -> dict[int, list[float]]:
    """Two imperfectly correlated series, arithmetic rather than seeded-random.

    A correlation strictly between 0 and 1 is what makes the diversification
    ratio informative: at 1 it collapses to 1 for every weighting, and the
    scale-invariance assertion would then pass on a constant.
    """
    return {
        1: [round(0.010 * math.sin(index * 0.6) + 0.002, 10) for index in range(24)],
        2: [round(0.008 * math.cos(index * 0.35) - 0.001, 10) for index in range(24)],
    }


def test_historical_kpi_publishes_every_acquired_field_with_its_documented_sign():
    """One assertion per field, so a half-applied sign flip cannot hide.

    An aggregate assertion would let two opposite conventions coexist inside one
    output for as long as they cancelled.
    """
    returns = _kpi_returns()
    computation = HistoricalKpiAnalytic().compute(
        HistoricalKpiParams(),
        make_context({1: returns, 2: returns}),
    )
    output = computation.output

    assert output.worst_realization is not None
    assert output.worst_realization < 0
    assert output.worst_realization_date is not None
    assert output.drawdown_at_risk is not None
    assert output.drawdown_at_risk < 0
    assert output.conditional_drawdown_at_risk is not None
    assert output.conditional_drawdown_at_risk < 0
    assert output.ulcer_index is not None
    assert output.ulcer_index > 0
    assert output.drawdown_confidence_level == pytest.approx(0.95, abs=1e-12)


def test_historical_kpi_worst_realization_names_the_day_the_loss_happened():
    returns = _kpi_returns()
    context = make_context({1: returns, 2: returns})
    expected_index = returns.index(min(returns))
    output = HistoricalKpiAnalytic().compute(HistoricalKpiParams(), context).output

    # Neither boundary: an off-by-one in either direction lands on a real date.
    assert 0 < expected_index < len(returns) - 1
    assert output.worst_realization == pytest.approx(min(returns), abs=1e-12)
    assert output.worst_realization_date == context.primary_return_dates[expected_index]
    assert output.worst_realization_date != context.primary_return_dates[expected_index - 1]
    assert output.worst_realization_date != context.primary_return_dates[expected_index + 1]


def test_historical_kpi_reports_no_worst_realization_when_every_day_gained():
    """The degenerate window is declared undefined, never floored at zero.

    ``worst_realization`` is constrained to ``le=0``; reporting ``0.0`` here
    would claim a loss that never happened and pair it with a profitable date.
    """
    returns = _all_positive_returns()
    assert len(returns) >= HistoricalKpiAnalytic.min_observations
    assert all(value > 0 for value in returns)

    computation = HistoricalKpiAnalytic().compute(
        HistoricalKpiParams(),
        make_context({1: returns, 2: returns}),
    )
    output = computation.output

    assert output.worst_realization is None
    assert output.worst_realization_date is None
    assert any(warning.code == "worst_realization_undefined" for warning in computation.warnings)


def test_worst_realization_keeps_a_flat_window_and_drops_only_a_winning_one():
    """The boundary sits at strictly positive, and the difference is not cosmetic.

    A window whose worst day merely broke even *is* expressible under ``le=0``:
    zero is the honest answer, and it comes with the date it happened. A window
    whose worst day gained is not expressible at all, so it degrades to ``None``.

    Relaxing the plugin guard from ``worst > 0`` to ``worst >= 0`` would collapse
    these two cases into one and report ``None`` for a flat window, which then
    contradicts ``max_drawdown`` reporting ``0.0`` for that same window. Both
    branches are asserted here because each one alone still passes after the
    change.
    """
    flat = [0.0] * HistoricalKpiAnalytic.min_observations
    computation = HistoricalKpiAnalytic().compute(HistoricalKpiParams(), make_context({1: flat, 2: flat}))
    output = computation.output

    assert output.worst_realization == pytest.approx(0.0, abs=1e-15)
    assert output.worst_realization_date is not None
    assert not any(warning.code == "worst_realization_undefined" for warning in computation.warnings)
    # The field that would contradict it if the flat case degraded to None.
    assert output.max_drawdown == pytest.approx(0.0, abs=1e-15)


def test_acquired_drawdown_family_collapses_on_a_monotonic_decline():
    """Every observation is in the tail, so the three drawdown figures coincide.

    A constant negative series is the shape where the quantile, the conditional
    mean beyond it and the maximum all have to return the same number: there is
    no observation outside the tail for them to disagree about. It is therefore
    the cheapest place to catch a sign flip or an off-by-one in the tail index,
    both of which survive a well-behaved series.

    The literals are riskfolio 7.0.1 on the same input, negated for the drawdown
    family and taken as-is for the ulcer index.
    """
    returns = [-0.01] * 8
    output = HistoricalKpiAnalytic().compute(HistoricalKpiParams(), make_context({1: returns, 2: returns})).output

    riskfolio_mdd_rel = 0.07725530557208005
    riskfolio_uci_rel = 0.04916919913152908

    assert output.max_drawdown == pytest.approx(-riskfolio_mdd_rel, rel=1e-12)
    assert output.drawdown_at_risk == pytest.approx(-riskfolio_mdd_rel, rel=1e-12)
    assert output.conditional_drawdown_at_risk == pytest.approx(-riskfolio_mdd_rel, rel=1e-12)
    assert output.ulcer_index == pytest.approx(riskfolio_uci_rel, rel=1e-12)
    assert output.worst_realization == pytest.approx(-0.01, abs=1e-15)

    # A flat series is the mirror case: no decline at all, and no negative zero.
    flat = [0.0] * 8
    flat_output = HistoricalKpiAnalytic().compute(HistoricalKpiParams(), make_context({1: flat, 2: flat})).output
    assert flat_output.max_drawdown == pytest.approx(0.0, abs=1e-15)
    assert flat_output.drawdown_at_risk == pytest.approx(0.0, abs=1e-15)
    assert flat_output.conditional_drawdown_at_risk == pytest.approx(0.0, abs=1e-15)
    assert flat_output.ulcer_index == pytest.approx(0.0, abs=1e-15)


def test_historical_kpi_drawdown_confidence_level_reaches_deeper_into_the_tail():
    returns = _kpi_returns()
    context = make_context({1: returns, 2: returns})
    default = HistoricalKpiAnalytic().compute(HistoricalKpiParams(), context).output
    stricter = HistoricalKpiAnalytic().compute(HistoricalKpiParams(drawdown_confidence_level=0.99), context).output

    assert default.drawdown_confidence_level == pytest.approx(0.95, abs=1e-12)
    assert stricter.drawdown_confidence_level == pytest.approx(0.99, abs=1e-12)
    assert stricter.drawdown_at_risk <= default.drawdown_at_risk
    # The two levels select distinct observations on this series, so a parameter
    # that never reached the measure would show up as equality rather than as a
    # bound that happens to hold.
    assert stricter.drawdown_at_risk != pytest.approx(default.drawdown_at_risk, abs=1e-9)
    assert stricter.conditional_drawdown_at_risk <= default.conditional_drawdown_at_risk


def test_historical_kpi_max_drawdown_is_still_the_one_from_summarize_drawdown():
    """No second field restates the peak-relative maximum drawdown.

    ``summarize_drawdown`` already produces MDD_Rel. A duplicate acquired field
    would give the product two names for one quantity, free to diverge.
    """
    returns = _kpi_returns()
    output = HistoricalKpiAnalytic().compute(HistoricalKpiParams(), make_context({1: returns, 2: returns})).output

    assert output.max_drawdown == pytest.approx(summarize_drawdown(returns).max_drawdown, abs=ORACLE_TOLERANCE)
    assert {name for name in RiskKpiOutput.model_fields if "drawdown" in name} == {
        "max_drawdown",
        "max_drawdown_duration_days",
        "drawdown_confidence_level",
        "drawdown_at_risk",
        "conditional_drawdown_at_risk",
    }


def test_risk_contribution_publishes_concentration_next_to_the_contributions():
    context = make_context(_contribution_returns(), mode=RiskMode.CURRENT_COMPOSITION)
    output = RiskContributionAnalytic().compute(RiskContributionParams(), context).output
    weights = [context.weights[asset_id] for asset_id in context.scope_asset_ids]

    assert output.effective_number_of_assets is not None
    assert output.effective_number_of_assets > 0
    assert output.effective_number_of_assets == pytest.approx(1.0 / math.fsum(weight**2 for weight in weights), abs=1e-12)
    assert output.diversification_ratio is not None
    assert output.diversification_ratio > 0
    # Cauchy-Schwarz: long-only weights cannot diversify below the weighted mean
    # of the standalone volatilities, so the ratio has a hard floor at one.
    assert output.diversification_ratio >= 1.0


def test_risk_contribution_keeps_cash_in_the_denominator_of_the_effective_count():
    """The pair of properties that makes the two fields meaningful together.

    Risk weights are ``position value / net worth``, the same denominator AI
    Export uses for ``nav_weight_percent``. Renormalizing to the invested part
    would make the product state two different concentrations for one portfolio,
    so the effective count *must* move when cash enters — while the ratio, being
    scale-invariant, must not.
    """
    base = make_context(_contribution_returns(), mode=RiskMode.CURRENT_COMPOSITION)
    invested = {1: 0.6, 2: 0.4}
    half_cash = {asset_id: weight * 0.5 for asset_id, weight in invested.items()}

    no_cash = RiskContributionAnalytic().compute(RiskContributionParams(), replace(base, weights=invested, cash_weight=0.0)).output
    with_cash = RiskContributionAnalytic().compute(RiskContributionParams(), replace(base, weights=half_cash, cash_weight=0.5)).output

    assert no_cash.cash_weight == pytest.approx(0.0, abs=1e-12)
    assert with_cash.cash_weight == pytest.approx(0.5, abs=1e-12)

    # Renormalizing the cash-heavy weights to the invested part makes these equal.
    assert with_cash.effective_number_of_assets != pytest.approx(no_cash.effective_number_of_assets, abs=1e-9)
    assert with_cash.effective_number_of_assets > no_cash.effective_number_of_assets
    assert no_cash.effective_number_of_assets == pytest.approx(1.0 / math.fsum(weight**2 for weight in invested.values()), abs=1e-12)
    assert with_cash.effective_number_of_assets == pytest.approx(1.0 / math.fsum(weight**2 for weight in half_cash.values()), abs=1e-12)

    # Same holdings, same correlation structure: the ratio is the one figure
    # comparable across portfolios holding different amounts of cash.
    assert with_cash.diversification_ratio == pytest.approx(no_cash.diversification_ratio, abs=1e-12)
    assert no_cash.diversification_ratio >= 1.0


def test_effective_number_of_assets_may_exceed_the_number_of_positions():
    """The consequence of the cash convention that no range constraint can show.

    ``1 / sum(w^2)`` is bounded above by the position count only when the weights
    sum to one. Risk weights do not: cash sits in the denominator without ever
    being a term, so a mostly-liquid portfolio reports an effective count *above*
    its own number of holdings. The shape below is the one measured end-to-end on
    the seeded portfolio — two positions weighing 0.2492 and 0.1591 of net worth,
    the remaining 0.5917 in cash — which reported 11.44 against two holdings.

    This is arithmetic, not a defect, and it is the price of agreeing with AI
    Export. It is pinned here because nothing else states it: the field is
    constrained ``gt=0`` only, so capping it at the holding count, renormalizing
    the weights, or building a caller that assumes ``NEA <= n`` would all pass
    every other test in this file while changing a ratified decision in silence.
    """
    weights = {1: 0.24919719587288608, 2: 0.15911534301518165}
    cash = 1.0 - math.fsum(weights.values())
    context = replace(
        make_context(_contribution_returns(), mode=RiskMode.CURRENT_COMPOSITION),
        weights=weights,
        cash_weight=cash,
    )

    output = RiskContributionAnalytic().compute(RiskContributionParams(), context).output

    assert output.effective_number_of_assets == pytest.approx(11.439431068254814, rel=1e-9)
    assert output.effective_number_of_assets > len(weights)

    # Renormalizing to the invested part is what would restore `NEA <= n`, and is
    # exactly the change this test exists to make visible.
    invested_total = math.fsum(weights.values())
    renormalized = 1.0 / math.fsum((weight / invested_total) ** 2 for weight in weights.values())
    assert renormalized == pytest.approx(1.9071719886819818, rel=1e-9)
    assert renormalized <= len(weights)

    # The ratio is unaffected: it is the figure that stays honest under cash.
    assert output.diversification_ratio >= 1.0


def test_historical_kpi_output_survives_the_discriminated_union_round_trip():
    returns = _kpi_returns()
    output = HistoricalKpiAnalytic().compute(HistoricalKpiParams(drawdown_confidence_level=0.975), make_context({1: returns, 2: returns})).output
    payload = output.model_dump(mode="json")

    assert payload["kind"] == "kpi"
    assert payload["worst_realization"] < 0
    assert payload["worst_realization_date"] == output.worst_realization_date.isoformat()
    assert payload["drawdown_confidence_level"] == pytest.approx(0.975, abs=1e-12)
    assert payload["ulcer_index"] > 0

    restored = TypeAdapter(RiskAnalyticOutput).validate_python(payload)

    assert isinstance(restored, RiskKpiOutput)
    assert restored.worst_realization == pytest.approx(output.worst_realization, abs=ORACLE_TOLERANCE)
    assert restored.worst_realization_date == output.worst_realization_date
    assert restored.drawdown_confidence_level == pytest.approx(0.975, abs=1e-12)
    assert restored.drawdown_at_risk == pytest.approx(output.drawdown_at_risk, abs=ORACLE_TOLERANCE)
    assert restored.conditional_drawdown_at_risk == pytest.approx(output.conditional_drawdown_at_risk, abs=ORACLE_TOLERANCE)
    assert restored.ulcer_index == pytest.approx(output.ulcer_index, abs=ORACLE_TOLERANCE)


# ---------------------------------------------------------------------------
# `excluded_weight` (developer's decision of 29/09/2026): Σ weights of the scope assets left without a
# series, stated next to `cash_weight` — the zero-return residual, clamped at zero, which those
# holdings belong to (G6). The split is the context's, stated as is: the plugin computes nothing new
# from it, and does not require the two to be nested (with negative true cash they are not).
# ---------------------------------------------------------------------------

WEIGHTED_PLUGINS = [
    pytest.param(RiskContributionAnalytic, RiskContributionParams, id="risk_contribution"),
    pytest.param(AssetRiskReturnAnalytic, AssetRiskReturnParams, id="asset_risk_return"),
]


@pytest.mark.parametrize(("analytic", "params"), WEIGHTED_PLUGINS)
def test_a_weighted_payload_states_the_excluded_part_of_its_cash(analytic, params):
    base = _risk_return_context()
    context = replace(base, excluded_weight=0.1)

    output = analytic().compute(params(), context).output
    reference = analytic().compute(params(), base).output

    assert output.excluded_weight == pytest.approx(0.1, abs=1e-15)
    # Still the whole residual.
    assert output.cash_weight == pytest.approx(context.cash_weight, abs=1e-15)
    # A label on the residual, not a new residual: nothing else moves.
    assert output.model_dump(exclude={"excluded_weight"}) == reference.model_dump(exclude={"excluded_weight"})


@pytest.mark.parametrize(("analytic", "params"), WEIGHTED_PLUGINS)
def test_with_negative_true_cash_the_payload_states_both_weights_as_they_are(analytic, params):
    """Net worth 500 against 600 of holdings: weights 0.8 and 0.4, the second without a series.

    The residual left by the priced holding is 0.2 and the excluded weight 0.4 — not nested, and the
    payload is produced all the same.
    """
    context = replace(_risk_return_context(), scope_asset_ids=(1,), weights={1: 0.8, 2: 0.4}, cash_weight=0.2, excluded_weight=0.4)

    output = analytic().compute(params(), context).output

    assert [item.weight for item in output.items] == pytest.approx([0.8])
    assert output.cash_weight == pytest.approx(0.2, abs=1e-15)
    assert output.excluded_weight == pytest.approx(0.4, abs=1e-15)


@pytest.mark.parametrize(("analytic", "params"), WEIGHTED_PLUGINS)
def test_a_weighted_payload_without_exclusions_states_a_zero_excluded_weight(analytic, params):
    output = analytic().compute(params(), _risk_return_context()).output

    assert output.excluded_weight == 0.0
    assert output.cash_weight == pytest.approx(0.25, abs=1e-15)
