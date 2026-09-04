"""Hand-derived mathematics and orchestration tests for rolling risk signals."""

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
)
from backend.app.schemas.signals import (
    SignalAreaSeries,
    SignalAvailabilityReason,
    SignalDomain,
    SignalExecutionContext,
    SignalPricePoint,
    SignalRequest,
    SignalStatus,
    SignalWarningCode,
)
from backend.app.services.risk.metrics import (
    annualized_sharpe,
    annualized_volatility,
    beta,
    compounded_return,
    daily_risk_free_rate,
    sample_covariance,
    sample_variance,
    underwater_drawdown,
)
from backend.app.services.signal_plugins.drawdown import (
    DrawdownParams,
    DrawdownPlugin,
)
from backend.app.services.signal_service import (
    SignalPreparedSeriesBundle,
    SignalService,
)


def _dates(count: int) -> list[date]:
    start = date(2026, 1, 1)
    return [start + timedelta(days=offset) for offset in range(count)]


def _prepared_series(
    asset_id: int,
    dates: list[date],
    prices: list[float],
    *,
    currency: str = "EUR",
) -> PreparedAssetSeries:
    valuations = AssetValuationSeries(
        asset_id=asset_id,
        target_currency=currency,
        points=[
            AssetValuationPoint(
                valuation_date=point_date,
                effective_price_date=point_date,
                is_price_carried_forward=False,
                native_close=Decimal(str(price)),
                native_currency=currency,
                target_close=Decimal(str(price)),
                target_currency=currency,
                price_source="risk_fixture",
            )
            for point_date, price in zip(dates, prices, strict=True)
        ],
    )
    returns = AssetReturnSeries(
        asset_id=asset_id,
        target_currency=currency,
        points=[
            AssetReturnPoint(
                date=current_date,
                previous_valuation_date=previous_date,
                value=current_price / previous_price - 1.0,
            )
            for previous_date, current_date, previous_price, current_price in zip(
                dates[:-1],
                dates[1:],
                prices[:-1],
                prices[1:],
                strict=True,
            )
        ],
    )
    return PreparedAssetSeries(valuations=valuations, returns=returns)


def _prepared_set(
    *series: PreparedAssetSeries,
) -> PreparedAssetSeriesSet:
    dates = [point.valuation_date for point in series[0].valuations.points]
    return PreparedAssetSeriesSet(
        requested_range=DateRangeModel(start=dates[0], end=dates[-1]),
        baseline_date=dates[0],
        effective_range=DateRangeModel(start=dates[1], end=dates[-1]),
        target_currency=series[0].valuations.target_currency,
        series=list(series),
        joint_valuation_dates=dates,
        joint_return_dates=dates[1:],
        n_observations=len(dates) - 1,
        calendar_days=(dates[-1] - dates[0]).days,
        annualization_factor=(len(dates) - 1) * 365 / (dates[-1] - dates[0]).days,
        calendar_coverage=1.0,
        fresh_quote_coverage=1.0,
        data_quality=DataQualityReport(),
        fx_fingerprint="0" * 64,
    )


def _price_points(dates: list[date], prices: list[float]) -> list[SignalPricePoint]:
    return [SignalPricePoint(date=point_date, close=Decimal(str(price))) for point_date, price in zip(dates, prices, strict=True)]


def _context(dates: list[date]) -> SignalExecutionContext:
    return SignalExecutionContext(
        domain=SignalDomain.ASSET,
        requested_range=DateRangeModel(start=dates[3], end=dates[-1]),
        source_reference="risk-fixture",
        target_currency="EUR",
    )


def test_risk_metrics_match_hand_derived_formulas():
    assert compounded_return([0.1, -0.1]) == pytest.approx(-0.01)
    assert sample_variance([1.0, 2.0, 3.0]) == pytest.approx(1.0)
    assert sample_covariance([1.0, 2.0, 3.0], [2.0, 4.0, 6.0]) == pytest.approx(2.0)
    assert annualized_volatility([0.1, -0.1], 365.0) == pytest.approx(math.sqrt(0.02) * math.sqrt(365.0))
    assert daily_risk_free_rate(0.05) == pytest.approx((1.05 ** (1 / 365)) - 1)

    daily_rf = daily_risk_free_rate(0.05)
    returns = [0.01, 0.02, 0.03]
    expected_sharpe = (sum(returns) / len(returns) - daily_rf) / math.sqrt(0.0001) * math.sqrt(365.0)
    assert annualized_sharpe(
        returns,
        365.0,
        annual_risk_free_rate=0.05,
    ) == pytest.approx(expected_sharpe)
    assert beta([0.02, -0.04, 0.06], [0.01, -0.02, 0.03]) == pytest.approx(2.0)
    assert beta([0.02, -0.04, 0.06], [0.0, 0.0, 0.0]) is None
    assert underwater_drawdown([100.0, 120.0, 90.0, 108.0, 130.0]) == pytest.approx([0.0, 0.0, -0.25, -0.1, 0.0])


@pytest.mark.asyncio
async def test_signal_service_computes_five_risk_plugins_from_prepared_series():
    dates = _dates(7)
    primary_prices = [100.0, 110.0, 99.0, 118.8, 112.86, 129.789, 119.40588]
    comparison_prices = [
        100.0,
        105.0,
        99.75,
        109.725,
        106.981875,
        115.005515625,
        110.405295,
    ]
    primary = _prepared_series(1, dates, primary_prices)
    comparison = _prepared_series(2, dates, comparison_prices)
    primary_set = _prepared_set(primary)
    pair_set = _prepared_set(primary, comparison)
    bundle = SignalPreparedSeriesBundle(
        primary_asset_id=1,
        series_sets={None: primary_set, 2: pair_set},
    )
    requests = [
        SignalRequest(
            instance_id="drawdown",
            signal_code="RISK_DRAWDOWN",
        ),
        SignalRequest(
            instance_id="volatility",
            signal_code="RISK_ROLLING_VOLATILITY",
            params={"window": 2},
        ),
        SignalRequest(
            instance_id="return",
            signal_code="RISK_ROLLING_RETURN",
            params={"window": 2},
        ),
        SignalRequest(
            instance_id="sharpe",
            signal_code="RISK_ROLLING_SHARPE",
            params={"window": 2, "risk_free_annual_rate": 0.0},
        ),
        SignalRequest(
            instance_id="beta",
            signal_code="RISK_ROLLING_BETA",
            params={"window": 2, "comparison_asset_id": 2},
        ),
    ]

    results = await SignalService().compute(
        requests,
        _price_points(dates, primary_prices),
        _context(dates),
        prepared_series_bundle=bundle,
    )

    assert [result.status for result in results] == [SignalStatus.OK] * 5
    assert all(result.risk_metadata is not None for result in results)
    assert all(result.data_quality is not None for result in results)
    assert results[-1].risk_metadata.comparison_asset_id == 2
    assert results[-1].series[0].points[-1].value == pytest.approx(2.0)
    assert results[0].series[0].points[-1].value == pytest.approx(-8.0)
    assert isinstance(results[0].series[0], SignalAreaSeries)

    rolling_return = results[2].series[0].points
    assert rolling_return[-1].value == pytest.approx(5.8)
    assert len(rolling_return) == 4


@pytest.mark.asyncio
async def test_flat_comparison_variance_is_unavailable_not_zero():
    dates = _dates(7)
    primary_prices = [100.0, 101.0, 99.0, 102.0, 100.0, 103.0, 101.0]
    comparison_prices = [50.0] * len(dates)
    primary = _prepared_series(1, dates, primary_prices)
    comparison = _prepared_series(2, dates, comparison_prices)
    bundle = SignalPreparedSeriesBundle(
        primary_asset_id=1,
        series_sets={
            None: _prepared_set(primary),
            2: _prepared_set(primary, comparison),
        },
    )

    result = (
        await SignalService().compute(
            [
                SignalRequest(
                    instance_id="beta",
                    signal_code="RISK_ROLLING_BETA",
                    params={"window": 2, "comparison_asset_id": 2},
                )
            ],
            _price_points(dates, primary_prices),
            _context(dates),
            prepared_series_bundle=bundle,
        )
    )[0]

    assert result.status == SignalStatus.UNAVAILABLE
    assert result.availability.reason_code == SignalAvailabilityReason.UNDEFINED_METRIC
    assert result.series == []


@pytest.mark.asyncio
async def test_partially_flat_sharpe_windows_are_explicitly_partial():
    dates = _dates(7)
    prices = [100.0, 110.0, 99.0, 108.9, 119.79, 107.811, 118.5921]
    primary = _prepared_series(1, dates, prices)
    bundle = SignalPreparedSeriesBundle(
        primary_asset_id=1,
        series_sets={None: _prepared_set(primary)},
    )

    result = (
        await SignalService().compute(
            [
                SignalRequest(
                    instance_id="sharpe",
                    signal_code="RISK_ROLLING_SHARPE",
                    params={"window": 2},
                )
            ],
            _price_points(dates, prices),
            _context(dates),
            prepared_series_bundle=bundle,
        )
    )[0]

    assert result.status == SignalStatus.PARTIAL
    assert result.availability.reason_code == SignalAvailabilityReason.PARTIAL_UNDEFINED_METRIC
    assert any(warning.code == SignalWarningCode.UNDEFINED_METRIC_WINDOW for warning in result.warnings)
    assert any(point.value is None for point in result.series[0].points)
    assert any(point.value is not None for point in result.series[0].points)


@pytest.mark.asyncio
async def test_missing_comparison_bundle_reports_domain_unavailability():
    dates = _dates(7)
    prices = [100.0, 101.0, 99.0, 102.0, 100.0, 103.0, 101.0]
    primary = _prepared_series(1, dates, prices)
    bundle = SignalPreparedSeriesBundle(
        primary_asset_id=1,
        series_sets={None: _prepared_set(primary)},
    )

    result = (
        await SignalService().compute(
            [
                SignalRequest(
                    instance_id="beta",
                    signal_code="RISK_ROLLING_BETA",
                    params={"window": 2, "comparison_asset_id": 2},
                )
            ],
            _price_points(dates, prices),
            _context(dates),
            prepared_series_bundle=bundle,
        )
    )[0]

    assert result.status == SignalStatus.UNAVAILABLE
    assert result.availability.reason_code == SignalAvailabilityReason.MISSING_COMPARISON_SERIES


# =============================================================================
# E1 — drawdown full_history: the running peak outlives the visible window
# =============================================================================


@pytest.mark.asyncio
async def test_drawdown_measures_visible_range_against_pre_window_peak():
    """THE E1 discriminating test.

    The series' ABSOLUTE peak (200) sits at dates[0], BEFORE the requested
    visible range (dates[3..6], see _context). With the full-history contract
    the visible drawdown is measured against that historical peak — the first
    visible point is -45%, not 0%. A window-relative implementation (peak =
    max of the visible points = 120) would read -8.3% there instead, so the
    exact values below discriminate the two.
    """
    dates = _dates(7)
    prices = [200.0, 150.0, 100.0, 110.0, 105.0, 120.0, 115.0]
    primary = _prepared_series(1, dates, prices)
    bundle = SignalPreparedSeriesBundle(
        primary_asset_id=1,
        series_sets={None: _prepared_set(primary)},
    )

    result = (
        await SignalService().compute(
            [SignalRequest(instance_id="drawdown", signal_code="RISK_DRAWDOWN")],
            _price_points(dates, prices),
            _context(dates),
            prepared_series_bundle=bundle,
        )
    )[0]

    assert result.status == SignalStatus.OK
    points = result.series[0].points
    # Sliced to the visible range: dates[3..6], four points.
    assert [point.date for point in points] == dates[3:]
    # Each visible point measured against the 200 peak: 110/200-1, 105/200-1,
    # 120/200-1, 115/200-1 — never reset to the window's own maximum.
    assert [point.value for point in points] == pytest.approx([-45.0, -47.5, -40.0, -42.5])


def test_drawdown_full_history_default_and_opt_out():
    """DrawdownParams defaults to full_history=True; opting out keeps the
    points-based warm-up (no full-history flag on the requirement/plan)."""
    context = _context(_dates(7))

    default_requirement = DrawdownPlugin.warmup_requirement(DrawdownParams(), context)
    assert DrawdownParams().full_history is True
    assert default_requirement.full_history is True
    assert default_requirement.total_points == 2

    opted_out = DrawdownPlugin.warmup_requirement(DrawdownParams(full_history=False), context)
    assert opted_out.full_history is False

    # Plan level: the opt-out means the fetch path stays on points-derived days.
    service = SignalService()
    plan_full = service.prepare_plan([SignalRequest(instance_id="dd", signal_code="RISK_DRAWDOWN")], context)
    assert plan_full.requires_full_history is True
    plan_windowed = service.prepare_plan(
        [SignalRequest(instance_id="dd", signal_code="RISK_DRAWDOWN", params={"full_history": False})],
        context,
    )
    assert plan_windowed.requires_full_history is False


def test_prepare_plan_marks_full_history_when_any_computation_declares_it():
    """A drawdown request in a mixed batch flips the plan-level flag; the fetch
    path (asset_source.get_prices_bulk) reads exactly this flag to decide
    between full-history load and points-derived warm-up days."""
    context = _context(_dates(7))
    plan = SignalService().prepare_plan(
        [
            SignalRequest(instance_id="drawdown", signal_code="RISK_DRAWDOWN"),
            SignalRequest(instance_id="return", signal_code="RISK_ROLLING_RETURN", params={"window": 2}),
        ],
        context,
    )
    assert plan.requires_full_history is True

    # Same batch without the drawdown → no full-history requirement.
    plan_without = SignalService().prepare_plan(
        [SignalRequest(instance_id="return", signal_code="RISK_ROLLING_RETURN", params={"window": 2})],
        context,
    )
    assert plan_without.requires_full_history is False
