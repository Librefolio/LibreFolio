"""Focused tests for the domain-neutral AI Export technical runner."""

from __future__ import annotations

import math
from copy import copy
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal

import pytest

from backend.app.schemas.ai_export import (
    AiExportAssetTargetReference,
    AiExportAssetTask,
    AiExportBrokerTask,
    AiExportDetailLevel,
    AiExportDomain,
    AiExportEvent,
    AiExportEventDirection,
    AiExportFxPairTargetReference,
    AiExportFxTask,
    AiExportPortfolioTask,
)
from backend.app.schemas.common import BackwardFillInfo, DateRangeModel
from backend.app.schemas.prices import AssetBackwardFillInfo, FAPricePoint
from backend.app.schemas.signals import (
    SignalAnnotation,
    SignalAnnotationDirection,
    SignalBandPoint,
    SignalBandSeries,
    SignalBandValueSource,
    SignalBarSeries,
    SignalLineSeries,
    SignalPricePoint,
    SignalResult,
    SignalSeriesKind,
    SignalSourceCapability,
    SignalStatus,
    SignalValuePoint,
    SignalVolumeKind,
)
from backend.app.services.ai_export.resolver import resolve_profile
from backend.app.services.ai_export.sampling import NumericPoint, sample_numeric_points
from backend.app.services.ai_export.technical import (
    combine_technical_results,
    deduplicate_and_limit_events,
    execute_technical_target,
    prepare_technical_target,
)
from backend.app.services.asset_source import AssetSourceManager
from backend.app.services.provider_registry import SignalPluginRegistry

ASSET_TARGET = AiExportAssetTargetReference(kind="asset", asset_id=11)
SECOND_ASSET_TARGET = AiExportAssetTargetReference(kind="asset", asset_id=12)
FX_TARGET = AiExportFxPairTargetReference(
    kind="fx_pair",
    base_currency="EUR",
    quote_currency="USD",
)
WINDOW = DateRangeModel(
    start=date(2026, 4, 1),
    end=date(2026, 6, 30),
)


class FakeExecutionService:
    def __init__(self, results):
        self.results = tuple(results)

    async def execute(
        self,
        plan,
        price_points,
        event_points=(),
        *,
        events_loaded=False,
        source_capability=None,
    ):
        self.captured_source_capability = source_capability
        return list(self.results)


def _profile(
    domain=AiExportDomain.ASSET,
    task=AiExportAssetTask.ASSET_SNAPSHOT,
    detail=AiExportDetailLevel.STANDARD,
):
    return resolve_profile(domain, task, detail)


def _prepare(
    *,
    profile=None,
    target=ASSET_TARGET,
    window=WINDOW,
    nav_weight_pct=None,
):
    return prepare_technical_target(
        profile or _profile(),
        target,
        window,
        "USD",
        "test:technical",
        nav_weight_pct,
    )


def _price_points(
    start: date,
    end: date,
    *,
    volume: bool = True,
    base: Decimal = Decimal("100"),
):
    points = []
    current = start
    index = 0
    while current <= end:
        cycle = Decimal(str(math.sin(index / 9))) * Decimal("2")
        close = base + Decimal(index) * Decimal("0.03") + cycle
        points.append(
            SignalPricePoint(
                date=current,
                open=close - Decimal("0.25"),
                high=close + Decimal("1.5"),
                low=close - Decimal("1.5"),
                close=close,
                volume=Decimal(1000 + index * 7) if volume else None,
            )
        )
        current += timedelta(days=1)
        index += 1
    return tuple(points)


def _output_spec(signal_code: str, key: str):
    plugin = SignalPluginRegistry.get_plugin(signal_code)
    assert plugin is not None
    spec = next(item for item in plugin.output_specs if item.key == key)
    return plugin, spec


def _scalar_series(signal_code: str, key: str, dates, values):
    _plugin, spec = _output_spec(signal_code, key)
    series_type = SignalBarSeries if spec.kind == SignalSeriesKind.BAR else SignalLineSeries
    return series_type(
        key=spec.key,
        label_key=spec.label_key,
        description_key=spec.description_key,
        semantic_id=spec.semantic_id,
        semantic_description=spec.semantic_description,
        unit=spec.unit,
        axis=spec.axis.model_copy(deep=True),
        view_transform=spec.view_transform,
        style=spec.style.model_copy(deep=True),
        points=[SignalValuePoint(date=point_date, value=value) for point_date, value in zip(dates, values, strict=True)],
    )


def _band_series(signal_code: str, key: str, dates, values):
    _plugin, spec = _output_spec(signal_code, key)
    return SignalBandSeries(
        key=spec.key,
        label_key=spec.label_key,
        description_key=spec.description_key,
        semantic_id=spec.semantic_id,
        semantic_description=spec.semantic_description,
        unit=spec.unit,
        axis=spec.axis.model_copy(deep=True),
        view_transform=spec.view_transform,
        style=spec.style.model_copy(deep=True),
        points=[
            SignalBandPoint(
                date=point_date,
                lower=lower,
                middle=middle,
                upper=upper,
            )
            for point_date, (lower, middle, upper) in zip(
                dates,
                values,
                strict=True,
            )
        ],
    )


def _result(
    instance_id: str,
    signal_code: str,
    series=(),
    *,
    status=SignalStatus.OK,
    params=None,
    annotations=(),
):
    plugin = SignalPluginRegistry.get_plugin(signal_code)
    return SignalResult.model_construct(
        instance_id=instance_id,
        signal_code=signal_code,
        implementation_version=(plugin.implementation_version if plugin is not None else "test"),
        normalized_params=params or {},
        status=status,
        series=list(series),
        annotations=list(annotations),
        warnings=[],
        availability=None,
        warmup=None,
        error=None,
    )


def _depth_policy_fixture():
    dates = tuple(WINDOW.end - timedelta(days=index) for index in range(219, -1, -1))
    window = DateRangeModel(start=dates[0], end=dates[-1])
    annotations = tuple(
        SignalAnnotation(
            key="price_ema_20",
            annotation_type="line_crossover",
            date=point_date,
            direction=SignalAnnotationDirection.UP,
            values={
                "left": Decimal("100"),
                "right": Decimal("99"),
                "difference": Decimal("1"),
            },
        )
        for point_date in dates
    )
    results = (
        _result(
            "ema_20",
            "EMA",
            (_scalar_series("EMA", "ema", dates, (Decimal("99"),) * len(dates)),),
            params={"period": 20, "offset": 0.0},
            annotations=annotations,
        ),
        _result(
            "ema_50",
            "EMA",
            (_scalar_series("EMA", "ema", dates, (Decimal("98"),) * len(dates)),),
            params={"period": 50, "offset": 0.0},
        ),
        _result(
            "ema_200",
            "EMA",
            (_scalar_series("EMA", "ema", dates, (Decimal("90"),) * len(dates)),),
            params={"period": 200, "offset": 0.0},
        ),
    )
    prices = tuple(SignalPricePoint(date=point_date, close=Decimal("100"), volume=Decimal("1000")) for point_date in dates)
    return dates, window, results, prices


@pytest.mark.parametrize(
    ("detail", "expected_limit", "expects_annotations"),
    (
        (AiExportDetailLevel.COMPACT, 10, False),
        (AiExportDetailLevel.STANDARD, 40, True),
        (AiExportDetailLevel.FULL, 120, True),
    ),
)
def test_prepare_converts_profile_requests_annotations_band_sources_and_limits(
    detail,
    expected_limit,
    expects_annotations,
):
    prepared = _prepare(profile=_profile(detail=detail))
    assert prepared is not None
    bundle = prepared.resolved_profile.technical_bundle
    assert bundle is not None

    assert [request.instance_id for request in prepared.execution_plan.requests] == [spec.instance_id for spec in bundle.signals]
    macd = next(request for request in prepared.execution_plan.requests if request.signal_code == "MACD")
    assert macd.params == {
        "fastPeriod": 12,
        "slowPeriod": 26,
        "signalPeriod": 9,
    }
    assert prepared.event_limit == expected_limit
    if expects_annotations:
        band_annotation = next(request for request in prepared.execution_plan.annotation_requests if request.key == "price_bollinger_lower")
        assert isinstance(band_annotation.right, SignalBandValueSource)
        assert band_annotation.right.series_key == "bands"
        assert band_annotation.right.component.value == "lower"
        assert all(request.limit == expected_limit and request.observed_only for request in prepared.execution_plan.annotation_requests)
    else:
        assert prepared.execution_plan.annotation_requests == ()
    assert prepared.execution_plan.context.observed_only is True
    assert prepared.execution_plan.context.data_policy.value == "strict_contiguous"


@pytest.mark.parametrize(
    ("supplied", "expected_gross"),
    (
        (Decimal("-20"), Decimal("20")),
        (Decimal("125"), Decimal("125")),
    ),
)
def test_prepare_normalizes_signed_unbounded_nav_weight_to_gross_magnitude(supplied, expected_gross):
    prepared = _prepare(nav_weight_pct=supplied)

    assert prepared is not None
    assert prepared.nav_weight_pct == expected_gross


def test_prepare_returns_none_for_profile_without_technical_bundle():
    profile = resolve_profile(
        AiExportDomain.PORTFOLIO,
        AiExportPortfolioTask.PERFORMANCE_ATTRIBUTION,
        AiExportDetailLevel.COMPACT,
    )

    assert (
        prepare_technical_target(
            profile,
            ASSET_TARGET,
            WINDOW,
            "USD",
            "test:none",
        )
        is None
    )


@pytest.mark.asyncio
async def test_performance_attribution_standard_emits_states_without_technical_or_events():
    dates, window, raw_results, prices = _depth_policy_fixture()
    profile = resolve_profile(
        AiExportDomain.PORTFOLIO,
        AiExportPortfolioTask.PERFORMANCE_ATTRIBUTION,
        AiExportDetailLevel.STANDARD,
    )
    prepared = _prepare(
        profile=profile,
        window=window,
        nav_weight_pct=Decimal("100"),
    )
    assert prepared is not None
    assert prepared.execution_plan.annotation_requests == ()
    assert len(raw_results[0].series[0].points) == 220
    assert len(raw_results[0].annotations) == 220

    result = await execute_technical_target(
        prepared,
        prices,
        signal_service=FakeExecutionService(raw_results),
    )

    assert result.technical_target is None
    assert result.events == ()
    assert {"price_vs_ema20", "price_vs_ema50", "price_vs_ema200", "ema20_vs_ema50"} <= {state.code for state in result.states}
    assert result.target_coverage.eligible is True
    assert result.target_coverage.analyzed is True
    assert {semantic.semantic_id for semantic in result.signal_semantics} == {
        "exponential_moving_average",
        "exponential_moving_average.value",
    }
    assert dates[-1] == result.states[-1].as_of


@pytest.mark.asyncio
async def test_latest_context_depth_forces_sampled_bundle_to_latest_and_keeps_events():
    _dates, window, raw_results, prices = _depth_policy_fixture()
    profile = resolve_profile(
        AiExportDomain.PORTFOLIO,
        AiExportPortfolioTask.PAC_PLANNING,
        AiExportDetailLevel.STANDARD,
    )
    prepared = _prepare(profile=profile, window=window)
    assert prepared is not None
    assert prepared.execution_plan.annotation_requests

    result = await execute_technical_target(
        prepared,
        prices,
        signal_service=FakeExecutionService(raw_results),
    )

    assert result.technical_target is not None
    assert result.events
    assert len(result.events) == 40
    assert result.states
    assert all(component.latest is not None and component.sampled_points == [] for signal in result.technical_target.signals for component in signal.components)


@pytest.mark.asyncio
async def test_technical_breadth_compact_emits_breadth_and_capped_events_without_technical():
    dates, window, raw_results, prices = _depth_policy_fixture()
    profile = resolve_profile(
        AiExportDomain.PORTFOLIO,
        AiExportPortfolioTask.TECHNICAL_BREADTH,
        AiExportDetailLevel.COMPACT,
    )
    prepared = _prepare(
        profile=profile,
        window=window,
        nav_weight_pct=Decimal("100"),
    )
    assert prepared is not None
    assert prepared.execution_plan.annotation_requests

    result = await execute_technical_target(
        prepared,
        prices,
        signal_service=FakeExecutionService(raw_results),
    )
    combined = combine_technical_results((result,))
    second_prepared = _prepare(
        profile=profile,
        target=SECOND_ASSET_TARGET,
        window=window,
    )
    assert second_prepared is not None
    second_result = await execute_technical_target(
        second_prepared,
        prices,
        signal_service=FakeExecutionService(raw_results),
    )
    combined_with_stale_result_limit = combine_technical_results(
        (
            result,
            replace(second_result, event_limit=1),
        )
    )
    metrics = {metric.code: metric for metric in combined.coverage.weighted_breadth.metrics}

    assert result.technical_target is None
    assert result.states
    assert len(result.events) == 10
    assert [event.date for event in result.events] == list(dates[-10:])
    assert combined.technical is None
    assert len(combined_with_stale_result_limit.events) == 10
    assert metrics["price_above_ema200"].asset_count == 1
    assert metrics["price_above_ema200"].portfolio_nav_weight_pct == Decimal("100.00")
    assert {semantic.semantic_id for semantic in result.signal_semantics} == {
        "exponential_moving_average",
        "exponential_moving_average.value",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "detail",
    (AiExportDetailLevel.STANDARD, AiExportDetailLevel.FULL),
)
async def test_technical_breadth_standard_and_full_keep_bundle_series_sampling(detail):
    dates, window, raw_results, prices = _depth_policy_fixture()
    profile = resolve_profile(
        AiExportDomain.PORTFOLIO,
        AiExportPortfolioTask.TECHNICAL_BREADTH,
        detail,
    )
    prepared = _prepare(profile=profile, window=window)
    assert prepared is not None

    result = await execute_technical_target(
        prepared,
        prices,
        signal_service=FakeExecutionService(raw_results),
    )

    assert result.technical_target is not None
    ema_20 = next(signal for signal in result.technical_target.signals if signal.instance_id == "ema_20")
    component = ema_20.components[0]
    expected_dates = [
        point.date
        for point in sample_numeric_points(
            tuple(NumericPoint(date=point_date, value=Decimal("99")) for point_date in dates),
            prepared.resolved_profile.detail_overlay.sampling,
        )
    ]
    assert component.latest is not None
    assert [point.date for point in component.sampled_points] == expected_dates
    assert component.sampled_points


def test_calculation_range_extends_before_three_month_window_for_ema200():
    prepared = _prepare(profile=_profile(detail=AiExportDetailLevel.FULL))
    assert prepared is not None

    assert prepared.execution_plan.max_history_points_before_visible >= 1200
    assert prepared.calculation_warmup_start == (WINDOW.start - timedelta(days=prepared.execution_plan.max_history_points_before_visible))
    assert prepared.calculation_range.start < WINDOW.start - timedelta(days=90)
    assert prepared.calculation_range.end == WINDOW.end


def test_calculation_start_clamps_safely_to_date_min():
    prepared = _prepare(
        profile=_profile(detail=AiExportDetailLevel.FULL),
        window=DateRangeModel(start=date.min, end=date.min),
    )
    assert prepared is not None
    assert prepared.calculation_warmup_start == date.min


@pytest.mark.asyncio
@pytest.mark.parametrize("domain", ("asset", "fx"))
async def test_real_standard_asset_and_fx_runs_have_sufficient_history(domain):
    if domain == "asset":
        profile = _profile()
        target = ASSET_TARGET
        volume = True
    else:
        profile = resolve_profile(
            AiExportDomain.FX,
            AiExportFxTask.FX_TREND_REVIEW,
            AiExportDetailLevel.STANDARD,
        )
        target = FX_TARGET
        volume = False
    prepared = _prepare(profile=profile, target=target)
    assert prepared is not None
    points = _price_points(
        prepared.calculation_range.start,
        prepared.calculation_range.end,
        volume=volume,
        base=Decimal("1.1") if domain == "fx" else Decimal("100"),
    )
    # Numeric volume alone must not grant eligibility: the runner only trusts
    # volume semantics when the caller threads an authoritative capability
    # derived from the observed source_plugin_key (e.g. Yahoo/Borsa-like
    # providers). Asset callers pass it explicitly here; FX has no meaningful
    # volume source and is left unset (unknown/false).
    source_capability = SignalSourceCapability(supports_meaningful_volume=True, volume_kind=SignalVolumeKind.TRADED_SHARES) if domain == "asset" else None

    result = await execute_technical_target(prepared, points, source_capability=source_capability)

    assert result.technical_target is not None
    signal_ids = [signal.instance_id for signal in result.technical_target.signals]
    assert {"ema_20", "ema_50", "ema_200"} <= set(signal_ids)
    assert len([signal for signal in result.technical_target.signals if signal.signal_code == "EMA"]) == 3
    assert all(signal.status.value in {"ok", "partial"} for signal in result.technical_target.signals)
    band_signal = next(signal for signal in result.technical_target.signals if signal.signal_code == "BOLLINGER")
    assert [component.component_code for component in band_signal.components] == [
        "bands.lower",
        "bands.middle",
        "bands.upper",
    ]
    assert result.target_coverage.analyzed is True
    if domain == "asset":
        assert result.target_coverage.volume_eligible is True
        assert result.target_coverage.volume_analyzed is True
    else:
        assert result.target_coverage.volume_eligible is False
        assert result.target_coverage.volume_analyzed is False


@pytest.mark.asyncio
async def test_manual_or_unknown_source_leaves_volume_signal_unanalyzed_despite_numeric_volume():
    """Regression guard for the AI Export/Signal source-capability contract:
    a MANUAL/unresolved source can still populate numeric ``volume`` values,
    but without an authoritative capability the runner must not treat that
    numeric presence as license to run volume-dependent signals (MFI/OBV).
    Structural eligibility (``volume_eligible``) stays true because the data
    is present; semantic analysis (``volume_analyzed``) must stay false.
    """
    prepared = _prepare(profile=_profile(), target=ASSET_TARGET)
    assert prepared is not None
    points = _price_points(
        prepared.calculation_range.start,
        prepared.calculation_range.end,
        volume=True,
    )

    # No source_capability threaded (as if derived from MANUAL/unregistered/
    # mixed sources): defaults to unknown/false.
    result = await execute_technical_target(prepared, points)

    assert result.target_coverage.analyzed is True
    assert result.target_coverage.volume_eligible is True
    assert result.target_coverage.volume_analyzed is False
    signal_ids = {signal.instance_id for signal in result.technical_target.signals} if result.technical_target is not None else set()
    assert "mfi_14" not in signal_ids


@pytest.mark.asyncio
async def test_backward_filled_only_source_is_not_evidence_and_leaves_volume_unanalyzed():
    """Integration guard: even when every observed point nominally carries a
    real provider's ``source_plugin_key`` (e.g. ``"yfinance"``), if all of
    them are backward-filled (no date was ever directly observed by that
    source) ``AssetSourceManager.derive_signal_source_capability`` must fail
    closed, and that closed verdict must actually suppress volume-dependent
    signal analysis once threaded through ``execute_technical_target``.
    """
    prepared = _prepare(profile=_profile(), target=ASSET_TARGET)
    assert prepared is not None

    fa_points = [
        FAPricePoint(
            date=prepared.calculation_range.start + timedelta(days=index),
            close=Decimal("100") + Decimal(index),
            volume=Decimal("1000"),
            source_plugin_key="yfinance",
            backward_fill_info=AssetBackwardFillInfo(actual_rate_date=prepared.calculation_range.start, days_back=index),
        )
        for index in range((prepared.calculation_range.end - prepared.calculation_range.start).days + 1)
    ]
    capability = AssetSourceManager.derive_signal_source_capability(fa_points)
    assert capability.supports_meaningful_volume is False

    points = _price_points(
        prepared.calculation_range.start,
        prepared.calculation_range.end,
        volume=True,
    )

    result = await execute_technical_target(prepared, points, source_capability=capability)

    assert result.target_coverage.volume_eligible is True
    assert result.target_coverage.volume_analyzed is False


@pytest.mark.asyncio
async def test_band_flattening_first_point_sampling_and_rounding_order():
    start = date(2026, 4, 1)
    dates = tuple(start + timedelta(days=index) for index in range(14))
    window = DateRangeModel(start=dates[0], end=dates[-1])
    prepared = _prepare(window=window)
    assert prepared is not None
    raw = tuple(
        NumericPoint(
            date=point_date,
            value=Decimal(f"{index + 1}.23456"),
        )
        for index, point_date in enumerate(dates)
    )
    bands = _band_series(
        "BOLLINGER",
        "bands",
        dates,
        tuple(
            (
                float(point.value),
                float(point.value + Decimal("1")),
                float(point.value + Decimal("2")),
            )
            for point in raw
        ),
    )
    fake = FakeExecutionService(
        (
            _result(
                "bollinger_20_2",
                "BOLLINGER",
                (bands,),
                params={"period": 20, "multiplier": 2.0},
            ),
        )
    )

    result = await execute_technical_target(
        prepared,
        _price_points(dates[0], dates[-1]),
        signal_service=fake,
    )

    assert result.technical_target is not None
    signal = result.technical_target.signals[0]
    assert [item.component_code for item in signal.components] == [
        "bands.lower",
        "bands.middle",
        "bands.upper",
    ]
    assert len({item.semantic_id for item in signal.components}) == 1
    expected_dates = [
        point.date
        for point in sample_numeric_points(
            raw,
            prepared.resolved_profile.detail_overlay.sampling,
        )
    ]
    lower = signal.components[0]
    assert [point.date for point in lower.sampled_points] == expected_dates
    assert lower.sampled_points[0].date == dates[0]
    assert lower.sampled_points[0].value == Decimal("1.2346")
    assert lower.latest.value == Decimal("14.2346")


@pytest.mark.asyncio
async def test_partial_with_points_is_included_and_unavailable_failed_are_omitted():
    dates = (WINDOW.start, WINDOW.start + timedelta(days=1))
    prepared = _prepare(
        profile=_profile(
            task=AiExportAssetTask.ASSET_TREND_ANALYSIS,
            detail=AiExportDetailLevel.COMPACT,
        ),
        window=DateRangeModel(start=dates[0], end=dates[-1]),
    )
    assert prepared is not None
    fake = FakeExecutionService(
        (
            _result(
                "ema_20",
                "EMA",
                (_scalar_series("EMA", "ema", dates, (99.0, 100.0)),),
                status=SignalStatus.PARTIAL,
                params={"period": 20, "offset": 0.0},
            ),
            _result(
                "rsi_14",
                "RSI",
                status=SignalStatus.UNAVAILABLE,
            ),
            _result(
                "macd_12_26_9",
                "MACD",
                status=SignalStatus.FAILED,
            ),
        )
    )

    result = await execute_technical_target(
        prepared,
        _price_points(dates[0], dates[-1]),
        signal_service=fake,
    )

    assert result.technical_target is not None
    assert [signal.instance_id for signal in result.technical_target.signals] == ["ema_20"]
    assert result.technical_target.signals[0].status.value == "partial"
    semantic_ids = {semantic.semantic_id for semantic in result.signal_semantics}
    assert semantic_ids == {
        "exponential_moving_average",
        "exponential_moving_average.value",
    }
    assert len(result.raw_signal_results) == 3


def _state_results(
    dates,
    *,
    close,
    adx,
    rsi,
    mfi,
    histogram,
    ppo_histogram,
    stoch_k,
    obv,
    bollinger,
    donchian,
):
    def scalar(instance, code, key, values, params=None):
        return _result(
            instance,
            code,
            (_scalar_series(code, key, dates, values),),
            params=params,
        )

    return (
        scalar(
            "ema_20",
            "EMA",
            "ema",
            (90.0, 90.0),
            {"period": 20, "offset": 0.0},
        ),
        scalar(
            "ema_50",
            "EMA",
            "ema",
            (95.0, 95.0),
            {"period": 50, "offset": 0.0},
        ),
        scalar(
            "ema_200",
            "EMA",
            "ema",
            (105.0, 105.0),
            {"period": 200, "offset": 0.0},
        ),
        scalar(
            "adx_14",
            "ADX",
            "adx",
            (adx, adx),
            {"period": 14},
        ),
        scalar(
            "rsi_14",
            "RSI",
            "rsi",
            (rsi, rsi),
            {"period": 14, "oversold": 30, "overbought": 70},
        ),
        scalar(
            "mfi_14",
            "MFI",
            "mfi",
            (mfi, mfi),
            {"period": 14, "oversold": 20, "overbought": 80},
        ),
        scalar(
            "macd_12_26_9",
            "MACD",
            "histogram",
            (histogram, histogram),
            {"fastPeriod": 12, "slowPeriod": 26, "signalPeriod": 9},
        ),
        scalar(
            "ppo_12_26_9",
            "PPO",
            "histogram",
            (ppo_histogram, ppo_histogram),
            {"fastPeriod": 12, "slowPeriod": 26, "signalPeriod": 9},
        ),
        scalar(
            "stoch_rsi_14_3",
            "STOCH_RSI",
            "k",
            (stoch_k, stoch_k),
            {
                "period": 14,
                "dPeriod": 3,
                "oversold": 20,
                "overbought": 80,
            },
        ),
        scalar(
            "obv",
            "OBV",
            "obv",
            obv,
            {},
        ),
        _result(
            "bollinger_20_2",
            "BOLLINGER",
            (
                _band_series(
                    "BOLLINGER",
                    "bands",
                    dates,
                    (bollinger, bollinger),
                ),
            ),
            params={"period": 20, "multiplier": 2.0},
        ),
        _result(
            "donchian_20",
            "DONCHIAN",
            (
                _band_series(
                    "DONCHIAN",
                    "channels",
                    dates,
                    (donchian, donchian),
                ),
            ),
            params={"period": 20},
        ),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("case", "expected"),
    (
        (
            {
                "close": 100,
                "adx": 25,
                "rsi": 70,
                "mfi": 50,
                "histogram": 0,
                "ppo_histogram": 5,
                "stoch_k": 20,
                "obv": (10, 10),
                "bollinger": (80, 100, 110),
                "donchian": (101, 110, 120),
            },
            {
                "price_vs_ema20": "above",
                "price_vs_ema50": "above",
                "price_vs_ema200": "below",
                "ema20_vs_ema50": "below",
                "adx_strength": "strong_trend",
                "rsi_state": "overbought",
                "mfi_state": "neutral",
                "macd_or_ppo_histogram": "neutral",
                "stochastic_rsi_k_state": "oversold",
                "obv_direction": "unchanged",
                "price_vs_bollinger": "inside",
                "price_vs_donchian": "below_lower",
            },
        ),
        (
            {
                "close": 130,
                "adx": 24.99,
                "rsi": 30,
                "mfi": 80,
                "histogram": 1,
                "ppo_histogram": -5,
                "stoch_k": 50,
                "obv": (10, 11),
                "bollinger": (80, 100, 110),
                "donchian": (80, 110, 140),
            },
            {
                "price_vs_ema20": "above",
                "price_vs_ema50": "above",
                "price_vs_ema200": "above",
                "ema20_vs_ema50": "below",
                "adx_strength": "weak_trend",
                "rsi_state": "oversold",
                "mfi_state": "overbought",
                "macd_or_ppo_histogram": "positive",
                "stochastic_rsi_k_state": "neutral",
                "obv_direction": "strengthening",
                "price_vs_bollinger": "above_upper",
                "price_vs_donchian": "inside",
            },
        ),
        (
            {
                "close": 70,
                "adx": 0,
                "rsi": 50,
                "mfi": 20,
                "histogram": -1,
                "ppo_histogram": 5,
                "stoch_k": 80,
                "obv": (11, 10),
                "bollinger": (80, 100, 110),
                "donchian": (40, 50, 60),
            },
            {
                "price_vs_ema20": "below",
                "price_vs_ema50": "below",
                "price_vs_ema200": "below",
                "ema20_vs_ema50": "below",
                "adx_strength": "weak_trend",
                "rsi_state": "neutral",
                "mfi_state": "oversold",
                "macd_or_ppo_histogram": "negative",
                "stochastic_rsi_k_state": "overbought",
                "obv_direction": "weakening",
                "price_vs_bollinger": "below_lower",
                "price_vs_donchian": "above_upper",
            },
        ),
    ),
)
async def test_every_derived_state_formula_and_neutral_labels(case, expected):
    dates = (date(2026, 6, 29), date(2026, 6, 30))
    window = DateRangeModel(start=dates[0], end=dates[-1])
    prepared = _prepare(
        profile=_profile(detail=AiExportDetailLevel.FULL),
        window=window,
    )
    assert prepared is not None
    fake = FakeExecutionService(
        _state_results(
            dates,
            **case,
        )
    )
    prices = tuple(
        SignalPricePoint(
            date=point_date,
            open=Decimal(str(case["close"])),
            high=Decimal(str(case["close"] + 2)),
            low=Decimal(str(case["close"] - 2)),
            close=Decimal(str(case["close"])),
            volume=Decimal("1000"),
        )
        for point_date in dates
    )

    result = await execute_technical_target(
        prepared,
        prices,
        signal_service=fake,
    )

    assert {state.code: state.state for state in result.states} == expected
    assert all(state.target == ASSET_TARGET and state.as_of == dates[-1] and state.signal_instance_id is not None and state.signal_code is not None and state.component_code is not None and state.value is not None for state in result.states)
    histogram = next(state for state in result.states if state.code == "macd_or_ppo_histogram")
    assert histogram.signal_code == "MACD"


@pytest.mark.asyncio
async def test_event_dedup_recent_cap_decimal_mapping_and_ascending_order():
    start = date(2026, 6, 1)
    dates = tuple(start + timedelta(days=index) for index in range(13))
    window = DateRangeModel(start=dates[0], end=dates[-1])
    prepared = _prepare(
        profile=resolve_profile(
            AiExportDomain.PORTFOLIO,
            AiExportPortfolioTask.TECHNICAL_BREADTH,
            AiExportDetailLevel.COMPACT,
        ),
        window=window,
    )
    assert prepared is not None
    annotations = [
        SignalAnnotation(
            key="price_ema_20",
            annotation_type="line_crossover",
            date=point_date,
            direction=(SignalAnnotationDirection.UP if index % 2 else SignalAnnotationDirection.DOWN),
            values={
                "left": 100.123456 + index,
                "right": 99.123456 + index,
                "difference": 1.0,
            },
        )
        for index, point_date in enumerate(dates)
    ]
    annotations.append(annotations[0].model_copy(deep=True))
    fake = FakeExecutionService(
        (
            _result(
                "ema_20",
                "EMA",
                (
                    _scalar_series(
                        "EMA",
                        "ema",
                        dates,
                        tuple(99 + index for index in range(len(dates))),
                    ),
                ),
                params={"period": 20, "offset": 0.0},
                annotations=annotations,
            ),
        )
    )

    result = await execute_technical_target(
        prepared,
        _price_points(dates[0], dates[-1]),
        signal_service=fake,
    )

    assert len(result.events) == 10
    assert [event.date for event in result.events] == list(dates[-10:])
    assert all(event.code == "price_ema_20" and event.signal_instance_id == "ema_20" and event.component_code == "ema" and all(isinstance(value, Decimal) for value in event.values.values()) for event in result.events)
    assert result.events[0].values["left"].as_tuple().exponent >= -4


def test_public_event_dedup_and_limit_helper_is_order_independent():
    events = tuple(
        AiExportEvent(
            target=ASSET_TARGET,
            date=date(2026, 6, day),
            code="price_crossed_above_ema200",
            signal_instance_id="ema_200",
            signal_code="EMA",
            direction=AiExportEventDirection.UP,
            values={"price": Decimal(day)},
        )
        for day in (1, 2, 3)
    )
    duplicated = (*events, events[0].model_copy(deep=True))

    forward = deduplicate_and_limit_events(duplicated, 2)
    reversed_result = deduplicate_and_limit_events(tuple(reversed(duplicated)), 2)

    assert forward == reversed_result
    assert [event.date for event in forward] == [date(2026, 6, 2), date(2026, 6, 3)]


@pytest.mark.asyncio
async def test_state_event_only_signal_can_analyze_target_without_technical_output():
    dates = (date(2026, 6, 29), date(2026, 6, 30))
    prepared = _prepare(
        window=DateRangeModel(start=dates[0], end=dates[-1]),
    )
    assert prepared is not None
    obv = _result(
        "obv",
        "OBV",
        (_scalar_series("OBV", "obv", dates, (0, 1000)),),
    )

    result = await execute_technical_target(
        prepared,
        _price_points(dates[0], dates[-1], volume=True),
        signal_service=FakeExecutionService((obv,)),
    )
    combined = combine_technical_results((result,))

    assert result.technical_target is None
    assert [(state.code, state.state) for state in result.states] == [("obv_direction", "strengthening")]
    assert result.target_coverage.analyzed is True
    assert result.target_coverage.volume_analyzed is True
    assert combined.technical is None
    assert combined.states == result.states
    assert {semantic.semantic_id for semantic in result.signal_semantics} == {"on_balance_volume", "on_balance_volume.value"}


@pytest.mark.asyncio
async def test_volume_eligibility_and_analysis_require_input_and_artifact():
    dates = (date(2026, 6, 29), date(2026, 6, 30))
    prepared = _prepare(
        window=DateRangeModel(start=dates[0], end=dates[-1]),
    )
    assert prepared is not None
    mfi = _result(
        "mfi_14",
        "MFI",
        (_scalar_series("MFI", "mfi", dates, (45, 55)),),
        params={"period": 14, "oversold": 20, "overbought": 80},
    )
    ema = _result(
        "ema_20",
        "EMA",
        (_scalar_series("EMA", "ema", dates, (99, 100)),),
        params={"period": 20, "offset": 0.0},
    )

    with_volume = await execute_technical_target(
        prepared,
        _price_points(dates[0], dates[-1], volume=True),
        signal_service=FakeExecutionService((mfi,)),
    )
    without_volume = await execute_technical_target(
        prepared,
        _price_points(dates[0], dates[-1], volume=False),
        signal_service=FakeExecutionService((mfi,)),
    )
    no_volume_artifact = await execute_technical_target(
        prepared,
        _price_points(dates[0], dates[-1], volume=True),
        signal_service=FakeExecutionService((ema,)),
    )

    assert (
        with_volume.target_coverage.volume_eligible,
        with_volume.target_coverage.volume_analyzed,
    ) == (True, True)
    assert (
        without_volume.target_coverage.volume_eligible,
        without_volume.target_coverage.volume_analyzed,
    ) == (False, False)
    assert (
        no_volume_artifact.target_coverage.volume_eligible,
        no_volume_artifact.target_coverage.volume_analyzed,
    ) == (True, False)


@pytest.mark.asyncio
async def test_no_observed_finite_close_is_ineligible_unanalyzed_and_excluded_from_breadth():
    point_date = date(2026, 6, 30)
    window = DateRangeModel(start=point_date, end=point_date)
    prepared = _prepare(
        window=window,
        nav_weight_pct=Decimal("100"),
    )
    assert prepared is not None
    ema_200 = _result(
        "ema_200",
        "EMA",
        (_scalar_series("EMA", "ema", (point_date,), (Decimal("90"),)),),
        params={"period": 200, "offset": 0.0},
    )
    cases = (
        (),
        (
            SignalPricePoint(
                date=point_date - timedelta(days=1),
                close=Decimal("100"),
                volume=Decimal("1000"),
            ),
        ),
        (
            SignalPricePoint(
                date=point_date,
                close=Decimal("100"),
                volume=Decimal("1000"),
                backward_fill_info=BackwardFillInfo(
                    actual_rate_date=point_date - timedelta(days=1),
                    days_back=1,
                ),
            ),
        ),
        (
            SignalPricePoint.model_construct(
                date=point_date,
                close=Decimal("NaN"),
                volume=Decimal("1000"),
                backward_fill_info=None,
            ),
        ),
    )

    for points in cases:
        result = await execute_technical_target(
            prepared,
            points,
            signal_service=FakeExecutionService((ema_200,)),
        )
        combined = combine_technical_results((result,))

        assert result.technical_target is None
        assert result.states == ()
        assert result.events == ()
        assert result.signal_semantics == ()
        assert result.target_coverage.eligible is False
        assert result.target_coverage.analyzed is False
        assert result.target_coverage.volume_eligible is False
        assert result.target_coverage.volume_analyzed is False
        assert dict(result.target_coverage.derived_states) == {}
        assert combined.coverage.technical.technically_eligible_assets == 0
        assert combined.coverage.technical.technically_analyzed_assets == 0
        assert combined.coverage.weighted_breadth.eligible_assets == 0
        assert all(metric.asset_count == 0 for metric in combined.coverage.weighted_breadth.metrics)


@pytest.mark.asyncio
async def test_short_observed_input_remains_eligible_without_computable_signals():
    point_date = date(2026, 6, 30)
    prepared = _prepare(
        window=DateRangeModel(start=point_date, end=point_date),
    )
    assert prepared is not None

    result = await execute_technical_target(
        prepared,
        (
            SignalPricePoint(
                date=point_date,
                close=Decimal("100"),
                volume=Decimal("1000"),
            ),
        ),
        signal_service=FakeExecutionService(()),
    )

    assert result.target_coverage.eligible is True
    assert result.target_coverage.analyzed is False
    assert result.target_coverage.volume_eligible is True
    assert result.target_coverage.volume_analyzed is False
    assert result.technical_target is None
    assert result.states == ()
    assert result.events == ()


async def _ema200_target_result(
    profile,
    target,
    *,
    nav_weight_pct,
    close,
    ema,
):
    dates = (date(2026, 6, 29), date(2026, 6, 30))
    prepared = _prepare(
        profile=profile,
        target=target,
        window=DateRangeModel(start=dates[0], end=dates[-1]),
        nav_weight_pct=nav_weight_pct,
    )
    assert prepared is not None
    fake = FakeExecutionService(
        (
            _result(
                "ema_200",
                "EMA",
                (_scalar_series("EMA", "ema", dates, (ema, ema)),),
                params={"period": 200, "offset": 0.0},
            ),
        )
    )
    prices = tuple(SignalPricePoint(date=point_date, close=Decimal(str(close))) for point_date in dates)
    return await execute_technical_target(
        prepared,
        prices,
        signal_service=fake,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("domain", "task"),
    (
        (
            AiExportDomain.PORTFOLIO,
            AiExportPortfolioTask.TECHNICAL_BREADTH,
        ),
        (
            AiExportDomain.BROKER,
            AiExportBrokerTask.BROKER_REVIEW,
        ),
    ),
)
async def test_multi_target_combine_accepts_same_portfolio_or_broker_profile_and_preserves_order(domain, task):
    profile = resolve_profile(
        domain,
        task,
        AiExportDetailLevel.STANDARD,
    )
    first = await _ema200_target_result(
        profile,
        ASSET_TARGET,
        nav_weight_pct=Decimal("40"),
        close=110,
        ema=100,
    )
    second = await _ema200_target_result(
        profile,
        SECOND_ASSET_TARGET,
        nav_weight_pct=Decimal("60"),
        close=90,
        ema=100,
    )

    combined = combine_technical_results((first, second))

    assert combined.technical is not None
    assert [target.target.asset_id for target in combined.technical.targets] == [11, 12]
    metrics = {metric.code: metric for metric in combined.coverage.weighted_breadth.metrics}
    assert combined.coverage.technical.technically_analyzed_assets == 2
    assert combined.coverage.technical.analyzed_nav_weight_pct == Decimal("100.00")
    assert metrics["price_above_ema200"].asset_count == 1
    assert metrics["price_above_ema200"].portfolio_nav_weight_pct == Decimal("40.00")
    assert metrics["price_below_ema200"].asset_count == 1
    assert metrics["price_below_ema200"].portfolio_nav_weight_pct == Decimal("60.00")
    assert len(combined.signal_semantics) == 2

    with pytest.raises(ValueError, match="unique"):
        combine_technical_results((first, first))


@pytest.mark.asyncio
async def test_combine_rejects_mixed_domain_task_detail_and_profile_versions():
    profile = resolve_profile(
        AiExportDomain.PORTFOLIO,
        AiExportPortfolioTask.TECHNICAL_BREADTH,
        AiExportDetailLevel.STANDARD,
    )
    first = await _ema200_target_result(
        profile,
        ASSET_TARGET,
        nav_weight_pct=Decimal("40"),
        close=110,
        ema=100,
    )
    same_profile_peer = await _ema200_target_result(
        profile,
        SECOND_ASSET_TARGET,
        nav_weight_pct=Decimal("60"),
        close=90,
        ema=100,
    )
    mixed_task = await _ema200_target_result(
        resolve_profile(
            AiExportDomain.PORTFOLIO,
            AiExportPortfolioTask.REBALANCING,
            AiExportDetailLevel.STANDARD,
        ),
        SECOND_ASSET_TARGET,
        nav_weight_pct=Decimal("60"),
        close=90,
        ema=100,
    )
    mixed_detail = await _ema200_target_result(
        resolve_profile(
            AiExportDomain.PORTFOLIO,
            AiExportPortfolioTask.TECHNICAL_BREADTH,
            AiExportDetailLevel.FULL,
        ),
        SECOND_ASSET_TARGET,
        nav_weight_pct=Decimal("60"),
        close=90,
        ema=100,
    )
    mixed_domain = await _ema200_target_result(
        resolve_profile(
            AiExportDomain.FX,
            AiExportFxTask.FX_TREND_REVIEW,
            AiExportDetailLevel.STANDARD,
        ),
        FX_TARGET,
        nav_weight_pct=Decimal("60"),
        close=0.9,
        ema=1.0,
    )

    for mixed in (mixed_task, mixed_detail, mixed_domain):
        with pytest.raises(ValueError, match="profile_id"):
            combine_technical_results((first, mixed))

    for field in ("profile_version", "schema_version"):
        changed_profile = copy(same_profile_peer.resolved_profile)
        object.__setattr__(
            changed_profile,
            field,
            getattr(changed_profile, field) + 1,
        )
        changed_result = replace(
            same_profile_peer,
            resolved_profile=changed_profile,
        )
        with pytest.raises(ValueError, match=field):
            combine_technical_results((first, changed_result))
