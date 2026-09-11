"""Hand-derived mathematics and orchestration tests for rolling risk signals."""

from __future__ import annotations

import math
from datetime import date, timedelta
from decimal import Decimal

import pytest

from backend.app.schemas.common import BackwardFillInfo, DateRangeModel
from backend.app.schemas.portfolio import DataQualityReport
from backend.app.schemas.prices import AssetBackwardFillInfo
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
    SignalCalendarReturnPointStatus,
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
from backend.app.services.signal_plugins.calendar_rolling_return import (
    CalendarRollingReturnParams,
    CalendarRollingReturnPlugin,
)
from backend.app.services.signal_plugins.drawdown import (
    DrawdownParams,
    DrawdownPlugin,
)
from backend.app.services.signal_plugins.rolling_return import (
    RollingReturnParams,
    RollingReturnPlugin,
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


# =============================================================================
# I10 — ASSET_CALENDAR_ROLLING_RETURN: calendar days, not observations
#
# The plugin is pure: it consumes the already-resolved, already-converted dense
# daily series the Asset adapter hands it and looks the reference price up by
# EXACT calendar date (t - N days). Everything below is hand-derived from the
# fixture prices; nothing here fetches, converts or resolves anything.
# =============================================================================

CALENDAR_SIGNAL_CODE = "ASSET_CALENDAR_ROLLING_RETURN"
CALENDAR_SERIES_KEY = "calendar_return"
CALENDAR_ALLOWED_WINDOWS = (7, 30, 90, 365)
CALENDAR_START = date(2026, 1, 1)  # a Thursday — the weekend fixtures rely on it


def _daily_points(
    start: date,
    closes: list[float],
    backfill: dict[date, BackwardFillInfo] | None = None,
) -> list[SignalPricePoint]:
    """Dense daily neutral input: one point per calendar day, no gaps."""
    resolved_backfill = backfill or {}
    points = []
    for offset, close in enumerate(closes):
        point_date = start + timedelta(days=offset)
        points.append(
            SignalPricePoint(
                date=point_date,
                close=Decimal(str(close)),
                backward_fill_info=resolved_backfill.get(point_date),
            )
        )
    return points


def _weekday_observed_points(start: date, count: int) -> list[SignalPricePoint]:
    """Dense daily input where weekends carry Friday's close forward.

    This is what the Asset adapter actually produces: a value for every
    calendar day, with `backward_fill_info` naming the real observation.
    """
    points: list[SignalPricePoint] = []
    last_observed_date: date | None = None
    last_close: Decimal | None = None
    for offset in range(count):
        current = start + timedelta(days=offset)
        if current.weekday() >= 5 and last_observed_date is not None:
            points.append(
                SignalPricePoint(
                    date=current,
                    close=last_close,
                    backward_fill_info=BackwardFillInfo(
                        actual_rate_date=last_observed_date,
                        days_back=(current - last_observed_date).days,
                    ),
                )
            )
            continue
        close = Decimal(str(100 + offset))
        points.append(SignalPricePoint(date=current, close=close))
        last_observed_date, last_close = current, close
    return points


def _price_on(points: list[SignalPricePoint], target: date) -> SignalPricePoint:
    return next(point for point in points if point.date == target)


def _calendar_context(dates: list[date], visible_start_index: int) -> SignalExecutionContext:
    return SignalExecutionContext(
        domain=SignalDomain.ASSET,
        requested_range=DateRangeModel(
            start=dates[visible_start_index],
            end=dates[-1],
        ),
        source_reference="calendar-fixture",
        target_currency="EUR",
    )


def _calendar_compute(points: list[SignalPricePoint], window_days: int | None = None):
    params = CalendarRollingReturnPlugin.validate_params({} if window_days is None else {"window_days": window_days})
    context = _calendar_context([point.date for point in points], 0)
    return CalendarRollingReturnPlugin().compute(points, [], params, context)


def _calendar_series(computation):
    return next(series for series in computation.series if series.key == CALENDAR_SERIES_KEY)


def _point_on(series, target: date):
    return next(point for point in series.points if point.date == target)


async def _calendar_result(
    points: list[SignalPricePoint],
    context: SignalExecutionContext,
    window_days: int,
):
    results = await SignalService().compute(
        [
            SignalRequest(
                instance_id="calendar",
                signal_code=CALENDAR_SIGNAL_CODE,
                params={"window_days": window_days},
            )
        ],
        points,
        context,
    )
    return next(result for result in results if result.instance_id == "calendar")


def test_calendar_window_counts_days_not_observations():
    """THE discriminating test for I10.

    Over 2026-01-10 → 2026-01-17 there are 8 calendar dates but only 6 distinct
    observations (two weekends carry Friday forward). An implementation that
    stepped back 7 *observations* would price 115 against 106; the calendar
    contract prices it against the value carried onto 2026-01-10, i.e. 108.
    """
    points = _weekday_observed_points(CALENDAR_START, 20)
    computation = _calendar_compute(points, window_days=7)
    series = _calendar_series(computation)
    current_date = date(2026, 1, 17)  # Saturday, carrying Friday 2026-01-16
    reference_date = date(2026, 1, 10)  # Saturday, carrying Friday 2026-01-09

    assert float(_price_on(points, current_date).close) == 115.0
    assert float(_price_on(points, reference_date).close) == 108.0

    point = _point_on(series, current_date)
    assert point.value == pytest.approx((115.0 / 108.0 - 1) * 100)
    assert point.value == pytest.approx(6.481481481481482)

    observation_count_reference = _price_on(points, date(2026, 1, 7))
    assert observation_count_reference.backward_fill_info is None
    assert float(observation_count_reference.close) == 106.0
    assert point.value != pytest.approx((115.0 / float(observation_count_reference.close) - 1) * 100)

    spanned = [item for item in points if reference_date <= item.date <= current_date]
    observation_dates = {item.backward_fill_info.actual_rate_date if item.backward_fill_info else item.date for item in spanned}
    assert len(spanned) == 8
    assert len(observation_dates) == 6

    assert point.provenance.status == SignalCalendarReturnPointStatus.AVAILABLE
    assert point.provenance.reference_target_date == reference_date
    assert point.provenance.reference_price_date == date(2026, 1, 9)
    assert point.provenance.reference_price_days_back == 1
    assert point.provenance.current_price_date == date(2026, 1, 16)
    assert point.provenance.current_price_days_back == 1


@pytest.mark.parametrize("window_days", CALENDAR_ALLOWED_WINDOWS)
def test_calendar_return_is_exact_for_every_allowed_window(window_days):
    points = _daily_points(CALENDAR_START, [100 + offset for offset in range(400)])
    series = _calendar_series(_calendar_compute(points, window_days=window_days))

    assert [point.date for point in series.points] == [point.date for point in points]
    for point, price_point in zip(series.points, points, strict=True):
        offset = (price_point.date - CALENDAR_START).days
        assert point.provenance.reference_target_date == price_point.date - timedelta(days=window_days)
        if offset < window_days:
            assert point.value is None
            assert point.provenance.status == SignalCalendarReturnPointStatus.MISSING_REFERENCE
            assert point.provenance.reference_price_date is None
        else:
            assert point.value == pytest.approx(((100.0 + offset) / (100.0 + offset - window_days) - 1) * 100)
            assert point.provenance.status == SignalCalendarReturnPointStatus.AVAILABLE

    last = _point_on(series, CALENDAR_START + timedelta(days=399))
    assert last.value == pytest.approx((499.0 / (499.0 - window_days) - 1) * 100)


def test_calendar_default_window_is_thirty_days():
    points = _daily_points(CALENDAR_START, [100 + offset for offset in range(100)])
    default_series = _calendar_series(_calendar_compute(points))
    explicit_series = _calendar_series(_calendar_compute(points, window_days=30))

    assert CalendarRollingReturnParams().window_days == 30
    assert [(point.date, point.value) for point in default_series.points] == [(point.date, point.value) for point in explicit_series.points]

    probe = _point_on(default_series, CALENDAR_START + timedelta(days=60))
    assert probe.provenance.reference_target_date == CALENDAR_START + timedelta(days=30)
    assert probe.value == pytest.approx((160.0 / 130.0 - 1) * 100)


def test_missing_reference_dates_are_null_with_a_typed_reason():
    points = _daily_points(CALENDAR_START, [100 + offset for offset in range(40)])
    computation = _calendar_compute(points, window_days=30)
    series = _calendar_series(computation)

    first = _point_on(series, CALENDAR_START)
    last_missing = _point_on(series, CALENDAR_START + timedelta(days=29))
    first_available = _point_on(series, CALENDAR_START + timedelta(days=30))

    assert first.value is None
    assert first.provenance.status == SignalCalendarReturnPointStatus.MISSING_REFERENCE
    assert first.provenance.reference_target_date == date(2025, 12, 2)
    assert last_missing.value is None
    assert last_missing.provenance.status == SignalCalendarReturnPointStatus.MISSING_REFERENCE
    assert first_available.value == pytest.approx((130.0 / 100.0 - 1) * 100)
    assert any(warning.code == SignalWarningCode.UNDEFINED_METRIC_WINDOW for warning in computation.warnings)


def test_invalid_current_and_reference_prices_carry_distinct_statuses():
    closes = [100.0 + offset for offset in range(80)]
    closes[35] = 0.0
    closes[50] = -5.0
    points = _daily_points(CALENDAR_START, closes)
    computation = _calendar_compute(points, window_days=30)
    series = _calendar_series(computation)

    invalid_current = _point_on(series, CALENDAR_START + timedelta(days=35))
    negative_current = _point_on(series, CALENDAR_START + timedelta(days=50))
    invalid_reference = _point_on(series, CALENDAR_START + timedelta(days=65))
    healthy = _point_on(series, CALENDAR_START + timedelta(days=66))

    assert invalid_current.value is None
    assert invalid_current.provenance.status == SignalCalendarReturnPointStatus.INVALID_CURRENT_PRICE
    assert negative_current.value is None
    assert negative_current.provenance.status == SignalCalendarReturnPointStatus.INVALID_CURRENT_PRICE
    assert invalid_reference.value is None
    assert invalid_reference.provenance.status == SignalCalendarReturnPointStatus.INVALID_REFERENCE_PRICE
    assert invalid_reference.provenance.reference_target_date == CALENDAR_START + timedelta(days=35)
    assert healthy.value == pytest.approx((166.0 / 136.0 - 1) * 100)
    assert healthy.provenance.status == SignalCalendarReturnPointStatus.AVAILABLE

    # A null value and a non-available status are two halves of one statement.
    for point in series.points:
        assert (point.value is None) == (point.provenance.status != SignalCalendarReturnPointStatus.AVAILABLE)
    assert any(warning.code == SignalWarningCode.UNDEFINED_METRIC_WINDOW for warning in computation.warnings)


def test_provenance_names_the_real_price_and_fx_observations():
    closes = [100.0 + offset for offset in range(20)]
    closes[3] = 101.0  # carried from 2026-01-02
    closes[10] = 109.0  # carried from 2026-01-10
    closes[15] = 114.0  # carried from 2026-01-15, no FX conversion involved
    backfill = {
        CALENDAR_START
        + timedelta(days=3): AssetBackwardFillInfo(
            actual_rate_date=CALENDAR_START + timedelta(days=1),
            days_back=2,
            fx_rate_date=CALENDAR_START,
            fx_days_back=3,
        ),
        CALENDAR_START
        + timedelta(days=10): AssetBackwardFillInfo(
            actual_rate_date=CALENDAR_START + timedelta(days=9),
            days_back=1,
            fx_rate_date=CALENDAR_START + timedelta(days=8),
            fx_days_back=2,
        ),
        CALENDAR_START
        + timedelta(days=15): BackwardFillInfo(
            actual_rate_date=CALENDAR_START + timedelta(days=14),
            days_back=1,
        ),
    }
    points = _daily_points(CALENDAR_START, closes, backfill=backfill)
    # Precondition: the neutral input really carries the FX half of the
    # staleness, otherwise the assertions below would be about the schema.
    assert _price_on(
        points,
        CALENDAR_START + timedelta(days=10),
    ).backward_fill_info.fx_rate_date == CALENDAR_START + timedelta(days=8)

    series = _calendar_series(_calendar_compute(points, window_days=7))

    backfilled = _point_on(series, CALENDAR_START + timedelta(days=10))
    assert backfilled.value == pytest.approx((109.0 / 101.0 - 1) * 100)
    assert backfilled.provenance.current_price_date == CALENDAR_START + timedelta(days=9)
    assert backfilled.provenance.current_price_days_back == 1
    assert backfilled.provenance.current_fx_date == CALENDAR_START + timedelta(days=8)
    assert backfilled.provenance.current_fx_days_back == 2
    assert backfilled.provenance.reference_target_date == CALENDAR_START + timedelta(days=3)
    assert backfilled.provenance.reference_price_date == CALENDAR_START + timedelta(days=1)
    assert backfilled.provenance.reference_price_days_back == 2
    assert backfilled.provenance.reference_fx_date == CALENDAR_START
    assert backfilled.provenance.reference_fx_days_back == 3

    price_only = _point_on(series, CALENDAR_START + timedelta(days=15))
    assert price_only.provenance.current_price_date == CALENDAR_START + timedelta(days=14)
    assert price_only.provenance.current_price_days_back == 1
    assert price_only.provenance.current_fx_date is None
    assert price_only.provenance.current_fx_days_back is None

    observed = _point_on(series, CALENDAR_START + timedelta(days=12))
    assert observed.value == pytest.approx((112.0 / 105.0 - 1) * 100)
    assert observed.provenance.current_price_date == CALENDAR_START + timedelta(days=12)
    assert observed.provenance.current_price_days_back == 0
    assert observed.provenance.reference_price_date == CALENDAR_START + timedelta(days=5)
    assert observed.provenance.reference_price_days_back == 0
    assert observed.provenance.current_fx_date is None
    assert observed.provenance.reference_fx_date is None


def test_calendar_return_does_not_invent_a_staleness_threshold():
    """A resolved point remains usable however old its source observation is.

    Resolution policy belongs to AssetSourceManager. The plugin consumes the
    dense point at the exact target date and reports, but does not reinterpret,
    the provenance it was given.
    """
    reference_target = CALENDAR_START
    actual_reference = reference_target - timedelta(days=120)
    points = _daily_points(
        CALENDAR_START,
        [100 + offset for offset in range(40)],
        backfill={
            reference_target: BackwardFillInfo(
                actual_rate_date=actual_reference,
                days_back=120,
            )
        },
    )

    point = _point_on(
        _calendar_series(_calendar_compute(points, window_days=30)),
        CALENDAR_START + timedelta(days=30),
    )

    assert point.value == pytest.approx((130.0 / 100.0 - 1) * 100)
    assert point.provenance.status == SignalCalendarReturnPointStatus.AVAILABLE
    assert point.provenance.reference_target_date == reference_target
    assert point.provenance.reference_price_date == actual_reference
    assert point.provenance.reference_price_days_back == 120


@pytest.mark.parametrize("window_days", CALENDAR_ALLOWED_WINDOWS)
def test_calendar_warmup_asks_for_the_whole_window_in_calendar_days(window_days):
    dates = [CALENDAR_START + timedelta(days=offset) for offset in range(400)]
    context = _calendar_context(dates, 380)
    params = CalendarRollingReturnPlugin.validate_params({"window_days": window_days})

    requirement = CalendarRollingReturnPlugin.warmup_requirement(params, context)

    # N pre-visible CALENDAR DAYS are the minimum that can reach t - N; asking
    # for more is allowed, asking for fewer silently truncates the first
    # visible points to null.
    assert requirement.total_points >= window_days
    assert requirement.full_history is False

    plan = SignalService().prepare_plan(
        [
            SignalRequest(
                instance_id="calendar",
                signal_code=CALENDAR_SIGNAL_CODE,
                params={"window_days": window_days},
            )
        ],
        context,
    )
    # asset_source turns exactly this number into pre-visible CALENDAR DAYS.
    assert plan.max_history_points_before_visible >= window_days
    assert plan.requires_full_history is False
    assert plan.max_prepared_history_points_before_visible == 0


@pytest.mark.asyncio
async def test_service_returns_one_calendar_point_per_visible_date():
    points = _daily_points(CALENDAR_START, [100 + offset for offset in range(120)])
    dates = [point.date for point in points]
    context = _calendar_context(dates, 90)

    result = await _calendar_result(points, context, 30)

    assert result.status == SignalStatus.OK
    assert result.availability.reason_code is None
    assert result.warmup.complete is True
    series = next(item for item in result.series if item.key == CALENDAR_SERIES_KEY)
    assert [point.date for point in series.points] == dates[90:]
    assert len(series.points) == 30
    for point in series.points:
        offset = (point.date - CALENDAR_START).days
        assert point.value == pytest.approx(((100.0 + offset) / (70.0 + offset) - 1) * 100)
        # Provenance must survive output normalization AND visible slicing.
        assert point.provenance.status == SignalCalendarReturnPointStatus.AVAILABLE
        assert point.provenance.reference_target_date == point.date - timedelta(days=30)


@pytest.mark.asyncio
async def test_one_unusable_reference_makes_the_visible_result_partial():
    closes = [100.0 + offset for offset in range(120)]
    closes[65] = 0.0  # warm-up date: only the visible point at +95 loses its reference
    points = _daily_points(CALENDAR_START, closes)
    context = _calendar_context([point.date for point in points], 90)

    result = await _calendar_result(points, context, 30)

    assert result.status == SignalStatus.PARTIAL
    assert result.availability.reason_code == SignalAvailabilityReason.PARTIAL_UNDEFINED_METRIC
    assert any(warning.code == SignalWarningCode.UNDEFINED_METRIC_WINDOW for warning in result.warnings)
    series = next(item for item in result.series if item.key == CALENDAR_SERIES_KEY)
    broken = _point_on(series, CALENDAR_START + timedelta(days=95))
    assert broken.value is None
    assert broken.provenance.status == SignalCalendarReturnPointStatus.INVALID_REFERENCE_PRICE
    assert broken.provenance.reference_target_date == CALENDAR_START + timedelta(days=65)
    assert all(point.value is not None for point in series.points if point.date != broken.date)


@pytest.mark.asyncio
async def test_every_visible_reference_unusable_is_unavailable_not_failed():
    closes = [100.0 + offset for offset in range(20)]
    for offset in range(8, 13):
        closes[offset] = 0.0
    points = _daily_points(CALENDAR_START, closes)
    context = _calendar_context([point.date for point in points], 15)

    result = await _calendar_result(points, context, 7)

    assert result.status == SignalStatus.UNAVAILABLE
    assert result.availability.reason_code == SignalAvailabilityReason.UNDEFINED_METRIC
    assert result.warmup.complete is True
    assert result.series == []


@pytest.mark.asyncio
async def test_visible_range_without_enough_calendar_history_is_unavailable():
    points = _daily_points(CALENDAR_START, [100 + offset for offset in range(40)])
    context = _calendar_context([point.date for point in points], 35)

    result = await _calendar_result(points, context, 90)

    assert result.status == SignalStatus.UNAVAILABLE
    assert result.availability.reason_code == SignalAvailabilityReason.INSUFFICIENT_HISTORY
    assert result.warmup.complete is False
    assert result.series == []


def test_legacy_rolling_return_defaults_and_contract_are_untouched():
    """RISK_ROLLING_RETURN still counts OBSERVATIONS, defaults to window=30 and
    stays publicly catalogued. I10 adds a plugin; it does not migrate this one."""
    context = _context(_dates(7))

    assert RollingReturnParams().window == 30
    assert RollingReturnPlugin.default_params() == {"window": 30}
    assert RollingReturnPlugin.signal_code == "RISK_ROLLING_RETURN"
    assert RollingReturnPlugin.catalog_visible is True
    assert RollingReturnPlugin.semantic_id == "rolling_compounded_return"
    assert [spec.key for spec in RollingReturnPlugin.output_specs] == ["rolling_return"]

    requirement = RollingReturnPlugin.warmup_requirement(RollingReturnParams(), context)
    assert requirement.minimum_points == 31
    assert requirement.stabilization_points == 0
    assert requirement.total_points == 31
    assert requirement.full_history is False
    assert RollingReturnPlugin.warmup_requirement(RollingReturnParams(window=2), context).total_points == 3


@pytest.mark.asyncio
async def test_calendar_sibling_does_not_disturb_the_legacy_rolling_return():
    dates = _dates(7)
    prices = [100.0, 110.0, 99.0, 118.8, 112.86, 129.789, 119.40588]
    bundle = SignalPreparedSeriesBundle(
        primary_asset_id=1,
        series_sets={None: _prepared_set(_prepared_series(1, dates, prices))},
    )
    price_points = _price_points(dates, prices)
    context = _context(dates)
    legacy_request = SignalRequest(instance_id="return", signal_code="RISK_ROLLING_RETURN", params={"window": 2})
    calendar_request = SignalRequest(
        instance_id="calendar",
        signal_code=CALENDAR_SIGNAL_CODE,
        params={"window_days": 7},
    )

    solo = await SignalService().compute([legacy_request], price_points, context, prepared_series_bundle=bundle)
    mixed = await SignalService().compute(
        [legacy_request, calendar_request],
        price_points,
        context,
        prepared_series_bundle=bundle,
    )

    solo_return = next(result for result in solo if result.instance_id == "return")
    mixed_return = next(result for result in mixed if result.instance_id == "return")
    mixed_calendar = next(result for result in mixed if result.instance_id == "calendar")

    solo_payload = solo_return.model_dump(mode="json")
    mixed_payload = mixed_return.model_dump(mode="json")
    solo_payload["risk_metadata"]["computed_at"] = "<runtime>"
    mixed_payload["risk_metadata"]["computed_at"] = "<runtime>"
    assert mixed_payload == solo_payload
    assert mixed_return.status == SignalStatus.OK
    legacy_series = next(item for item in mixed_return.series if item.key == "rolling_return")
    assert len(legacy_series.points) == 4
    assert _point_on(legacy_series, dates[-1]).value == pytest.approx(5.8)
    # The hidden sibling is planned and executed; it simply has no 7-day history.
    assert mixed_calendar.signal_code == CALENDAR_SIGNAL_CODE
    assert mixed_calendar.status == SignalStatus.UNAVAILABLE
    assert mixed_calendar.availability.reason_code == SignalAvailabilityReason.INSUFFICIENT_HISTORY
