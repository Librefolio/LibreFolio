"""Pure plugin tests for deterministic multi-asset risk analytics."""

from __future__ import annotations

import math
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal

import pytest
from pydantic import TypeAdapter

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
    RiskCompositionPolicy,
    RiskDrawdownRecoveryStatus,
    RiskKpiOutput,
    RiskMode,
    RiskReturnBasis,
    RiskScopeKind,
    RiskStressApplicationRule,
    RiskStressMethod,
    RiskValueStatus,
)
from backend.app.schemas.risk_scenarios import RiskScenarioDimension
from backend.app.services.provider_registry import RiskAnalyticRegistry
from backend.app.services.risk import acquired
from backend.app.services.risk.base import (
    RiskAssetClassification,
    RiskExecutionContext,
    RiskHistoricalReplayContext,
    RiskUnavailableError,
)
from backend.app.services.risk.metrics import summarize_drawdown
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
