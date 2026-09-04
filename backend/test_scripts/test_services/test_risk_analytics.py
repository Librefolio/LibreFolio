"""Pure plugin tests for deterministic multi-asset risk analytics."""

from __future__ import annotations

import math
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal

import pytest

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
    RiskCompositionPolicy,
    RiskDrawdownRecoveryStatus,
    RiskMode,
    RiskReturnBasis,
    RiskScopeKind,
    RiskStressApplicationRule,
    RiskStressMethod,
    RiskValueStatus,
)
from backend.app.schemas.risk_scenarios import RiskScenarioDimension
from backend.app.services.provider_registry import RiskAnalyticRegistry
from backend.app.services.risk.base import (
    RiskAssetClassification,
    RiskExecutionContext,
    RiskHistoricalReplayContext,
    RiskUnavailableError,
)
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

    assert computation.output.portfolio_return == pytest.approx(0.05)
    assert computation.output.impact_amount == Decimal("10.000")
    assert [impact.asset_id for impact in computation.output.impacts] == [1, 2]
    assert computation.output.impacts[1].shock_return == 0
    audit = computation.historical_replay_audit
    assert audit.excluded_weight_total == pytest.approx(0.25)
    assert audit.excluded_assets[0].treatment.value == "zero_return_residual"


def test_historical_replay_requires_proxy_or_exclusion_for_missing_original():
    context = make_context(
        {1: [0.01] * 20},
        scope_kind=RiskScopeKind.ASSET_SET,
        mode=RiskMode.CURRENT_COMPOSITION,
        scope_asset_ids=(1, 2),
    )

    with pytest.raises(RiskUnavailableError) as exc_info:
        StressAnalytic().compute(
            StressParams(
                method=RiskStressMethod.HISTORICAL_REPLAY,
                replay_range=context.requested_range,
            ),
            context,
        )

    assert exc_info.value.code.value == "insufficient_history"
    assert exc_info.value.details == {
        "asset_id": 2,
        "return_source_asset_id": 2,
        "reason": "insufficient_history",
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
