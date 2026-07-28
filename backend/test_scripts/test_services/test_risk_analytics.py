"""Pure plugin tests for deterministic multi-asset risk analytics."""

from __future__ import annotations

import math
from datetime import date, timedelta
from decimal import Decimal

import pytest

from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.portfolio import DataQualityReport
from backend.app.schemas.risk import (
    AssetReturnPoint,
    AssetReturnSeries,
    AssetValuationPoint,
    AssetValuationSeries,
    PreparedAssetSeries,
    PreparedAssetSeriesSet,
    RiskCompositionPolicy,
    RiskMode,
    RiskReturnBasis,
    RiskScopeKind,
    RiskStressMethod,
    RiskValueStatus,
)
from backend.app.services.provider_registry import RiskAnalyticRegistry
from backend.app.services.risk.base import RiskExecutionContext
from backend.app.services.risk.quant.optimization_engine import (
    clear_optimization_cache,
)
from backend.app.services.risk.quant.workers import (
    shutdown_quant_worker_pools,
)
from backend.app.services.risk_plugins.comparison import (
    ComparisonAnalytic,
    ComparisonParams,
)
from backend.app.services.risk_plugins.correlation import (
    CorrelationAnalytic,
    CorrelationParams,
)
from backend.app.services.risk_plugins.historical_var import (
    HistoricalVarAnalytic,
    HistoricalVarParams,
)
from backend.app.services.risk_plugins.portfolio_kpi import (
    PortfolioKpiAnalytic,
    PortfolioKpiParams,
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
) -> PreparedAssetSeriesSet:
    baseline = date(2026, 1, 1)
    observations = len(next(iter(returns_by_asset.values())))
    assert all(len(values) == observations for values in returns_by_asset.values())
    valuation_dates = [baseline + timedelta(days=index) for index in range(observations + 1)]
    return_dates = valuation_dates[1:]
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
        calendar_days=observations,
        annualization_factor=365.0,
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
) -> RiskExecutionContext:
    prepared = make_prepared_set(returns_by_asset)
    primary = next(item for item in prepared.series if item.returns.asset_id == primary_asset_id)
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
        primary_return_basis=RiskReturnBasis.TWRR if mode == RiskMode.HISTORICAL else RiskReturnBasis.PRICE_ONLY,
        annualization_factor=prepared.annualization_factor,
        calendar_days=prepared.calendar_days,
        coverage=prepared.calendar_coverage,
        data_quality=prepared.data_quality,
        weights={1: 0.5, 2: 0.25},
        asset_values={1: Decimal("100"), 2: Decimal("50")},
        cash_weight=0.25,
        scope_value=Decimal("200"),
    )


def test_registry_discovers_all_deterministic_analytics():
    definitions = RiskAnalyticRegistry.list_definitions()
    assert [definition.analytic_code for definition in definitions] == [
        "comparison",
        "correlation",
        "historical_var",
        "portfolio_kpi",
        "portfolio_optimization",
        "risk_contribution",
        "simulation",
        "stress",
    ]


def test_portfolio_kpi_consumes_primary_twrr_and_observed_annualization():
    returns = [0.01, -0.005] * 10
    computation = PortfolioKpiAnalytic().compute(
        PortfolioKpiParams(),
        make_context({1: returns, 2: returns}),
    )
    output = computation.output

    assert output.volatility > 0
    assert output.max_drawdown <= 0
    assert output.max_drawdown_duration_days >= 0
    assert output.sharpe is not None
    assert computation.risk_free is not None
    assert computation.risk_free.annual_rate == 0


def test_correlation_marks_flat_cells_undefined_without_inventing_zero():
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


def test_stress_projects_hypothetical_percentages_and_amounts():
    context = make_context(
        {1: [0.01] * 20, 2: [0.0] * 20},
        mode=RiskMode.CURRENT_COMPOSITION,
    )
    computation = StressAnalytic().compute(
        StressParams(
            method=RiskStressMethod.HYPOTHETICAL,
            shocks={"1": -0.2, "2": 0.1},
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


def test_historical_replay_uses_current_buy_and_hold_policy():
    context = make_context(
        {1: [0.1, 0.0] + [0.0] * 18, 2: [0.0, 0.1] + [0.0] * 18},
        mode=RiskMode.CURRENT_COMPOSITION,
    )
    replay_range = DateRangeModel(
        start=date(2026, 1, 2),
        end=date(2026, 1, 3),
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
                paths=256,
                seed=123,
            ),
            context,
        )
    finally:
        await shutdown_quant_worker_pools()
    output = computation.output

    assert output.process.value == "gbm"
    assert output.sampling.value == "mc"
    assert output.aggregation_policy.value == "current_buy_and_hold"
    assert output.costs_included is False
    assert output.cash_flows_included is False
    assert output.rebalanced is False
    assert len(output.percentile_bands) == 11
    assert computation.n_observations == 40
    assert computation.seed == 123
    assert "quantlib" in computation.method
    assert PortfolioOptimizationAnalytic.output_kind.value == "optimization"


@pytest.mark.asyncio
async def test_portfolio_optimization_executes_for_all_supported_scopes():
    clear_optimization_cache()
    returns_by_asset = {
        1: [0.001 + 0.01 * math.sin(index / 4) for index in range(60)],
        2: [0.0005 + 0.007 * math.cos(index / 5) for index in range(60)],
    }
    outputs = []
    try:
        for scope_kind in (
            RiskScopeKind.PORTFOLIO,
            RiskScopeKind.BROKER,
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
