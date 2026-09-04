"""Numerical and contract tests for EMA, RSI, MACD and Bollinger plugins."""

from __future__ import annotations

import json
from datetime import date

import numpy as np
import pytest
import talib

from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.signals import (
    SignalBandSeries,
    SignalDomain,
    SignalExecutionContext,
    SignalRequest,
    SignalSeriesKind,
    SignalStatus,
)
from backend.app.services.provider_registry import SignalPluginRegistry
from backend.app.services.signal_plugins import bollinger as bollinger_module
from backend.app.services.signal_plugins import ema as ema_module
from backend.app.services.signal_plugins import macd as macd_module
from backend.app.services.signal_plugins import rsi as rsi_module
from backend.app.services.signal_plugins.bollinger import (
    BollingerSignalParams,
    BollingerSignalPlugin,
)
from backend.app.services.signal_plugins.ema import (
    EmaSignalParams,
    EmaSignalPlugin,
)
from backend.app.services.signal_plugins.macd import (
    MacdSignalParams,
    MacdSignalPlugin,
)
from backend.app.services.signal_plugins.rsi import (
    RsiSignalParams,
    RsiSignalPlugin,
)
from backend.app.services.signal_service import SignalService
from backend.test_scripts.fixtures.signals.plugin_test_utils import (
    VISIBLE_POINTS,
    execution_context,
    frame_to_points,
    load_signal_frames,
    normalized_error,
    numeric_matrix,
)
from backend.test_scripts.fixtures.signals.sample_points import (
    make_signal_price_points,
)

CORE_CODES = {"EMA", "RSI", "MACD", "BOLLINGER"}


@pytest.fixture(scope="module")
def frames():
    return load_signal_frames(
        (
            "flat",
            "trend",
            "volatile",
            "scale_low",
            "scale_high",
        )
    )


@pytest.fixture(scope="module")
def neutral_points(frames):
    return {name: frame_to_points(frame) for name, frame in frames.items()}


def ts_ema(values: np.ndarray, period: int) -> np.ndarray:
    alpha = 2 / (period + 1)
    output = np.empty_like(values)
    output[0] = values[0]
    for index in range(1, len(values)):
        output[index] = alpha * values[index] + (1 - alpha) * output[index - 1]
    return output


def ts_rsi(values: np.ndarray, period: int) -> np.ndarray:
    output = np.full_like(values, 50.0)
    average_gain = 0.0
    average_loss = 0.0
    alpha = 1 / period
    for index in range(1, len(values)):
        delta = values[index] - values[index - 1]
        gain = max(delta, 0.0)
        loss = max(-delta, 0.0)
        if index <= period:
            average_gain += gain / period
            average_loss += loss / period
            if index < period:
                continue
        else:
            average_gain = alpha * gain + (1 - alpha) * average_gain
            average_loss = alpha * loss + (1 - alpha) * average_loss
        output[index] = 100.0 if average_loss == 0 else (0.0 if average_gain == 0 else 100 * average_gain / (average_gain + average_loss))
    return output


def ts_macd(
    values: np.ndarray,
    fast: int,
    slow: int,
    signal: int,
) -> np.ndarray:
    fast_values = ts_ema(values, fast)
    slow_values = ts_ema(values, slow)
    macd_values = fast_values - slow_values
    signal_values = ts_ema(macd_values, signal)
    histogram = macd_values - signal_values
    return np.column_stack([macd_values, signal_values, histogram])


def ts_bollinger(
    values: np.ndarray,
    period: int,
    multiplier: float,
) -> np.ndarray:
    lower = np.empty_like(values)
    middle = np.empty_like(values)
    upper = np.empty_like(values)
    for index in range(len(values)):
        window = values[max(0, index - period + 1) : index + 1]
        average = float(np.mean(window))
        deviation = float(np.std(window, ddof=0))
        lower[index] = average - multiplier * deviation
        middle[index] = average
        upper[index] = average + multiplier * deviation
    return np.column_stack([lower, middle, upper])


def test_registry_discovers_core_plugins_and_schema_driven_catalog():
    assert CORE_CODES.issubset(set(SignalPluginRegistry.list_plugin_codes()))
    definitions = {item.signal_code: item for item in SignalPluginRegistry.list_definitions() if item.signal_code in CORE_CODES}

    assert definitions["MACD"].default_params == {
        "fastPeriod": 12,
        "slowPeriod": 26,
        "signalPeriod": 9,
    }
    assert set(definitions["MACD"].params_schema["properties"]) == {
        "fastPeriod",
        "slowPeriod",
        "signalPeriod",
    }
    assert definitions["RSI"].output_specs[0].supports_value_regions is True
    assert definitions["BOLLINGER"].output_specs[0].kind == SignalSeriesKind.BAND
    serialized = json.dumps({code: definition.model_dump(mode="json") for code, definition in definitions.items()})
    for forbidden in ('"color"', '"lineWidth"', '"lineType"', '"marker"'):
        assert forbidden not in serialized


def test_parameter_validation_and_aliases():
    assert EmaSignalParams(period=20, offset=5).period == 20
    with pytest.raises(ValueError):
        EmaSignalParams(period=1)
    with pytest.raises(ValueError):
        RsiSignalParams(oversold=70, overbought=60)
    macd = MacdSignalParams.model_validate(
        {
            "fastPeriod": 5,
            "slowPeriod": 20,
            "signalPeriod": 7,
        }
    )
    assert macd.model_dump(mode="json", by_alias=True) == {
        "fastPeriod": 5,
        "slowPeriod": 20,
        "signalPeriod": 7,
    }
    with pytest.raises(ValueError):
        MacdSignalParams(
            fastPeriod=20,
            slowPeriod=20,
            signalPeriod=9,
        )
    with pytest.raises(ValueError):
        BollingerSignalParams(multiplier=0.1)


@pytest.mark.parametrize(
    ("module", "function_name", "plugin_class", "params"),
    [
        (ema_module, "ema", EmaSignalPlugin, {"period": 14}),
        (rsi_module, "rsi", RsiSignalPlugin, {"period": 14}),
        (
            macd_module,
            "macd",
            MacdSignalPlugin,
            {
                "fastPeriod": 12,
                "slowPeriod": 26,
                "signalPeriod": 9,
            },
        ),
        (
            bollinger_module,
            "bbands",
            BollingerSignalPlugin,
            {"period": 20},
        ),
    ],
)
def test_each_plugin_explicitly_requests_talib(
    monkeypatch,
    module,
    function_name,
    plugin_class,
    params,
    neutral_points,
):
    original = getattr(module.ta, function_name)
    calls: list[dict] = []

    def tracked(*args, **kwargs):
        calls.append(kwargs.copy())
        return original(*args, **kwargs)

    monkeypatch.setattr(module.ta, function_name, tracked)
    points = neutral_points["volatile"][-500:]
    model = plugin_class.validate_params(params)
    plugin_class().compute(
        points,
        [],
        model,
        execution_context(points),
    )

    assert calls
    assert calls[0]["talib"] is True


def test_core_plugins_match_direct_talib(neutral_points):
    points = neutral_points["volatile"][-500:]
    close = np.asarray(
        [float(point.close) for point in points],
        dtype=float,
    )
    context = execution_context(points)

    ema = numeric_matrix(
        EmaSignalPlugin().compute(
            points,
            [],
            EmaSignalParams(period=14),
            context,
        )
    )[:, 0]
    rsi = numeric_matrix(
        RsiSignalPlugin().compute(
            points,
            [],
            RsiSignalParams(period=14),
            context,
        )
    )[:, 0]
    macd = numeric_matrix(
        MacdSignalPlugin().compute(
            points,
            [],
            MacdSignalParams(),
            context,
        )
    )
    bands = numeric_matrix(
        BollingerSignalPlugin().compute(
            points,
            [],
            BollingerSignalParams(),
            context,
        )
    )
    direct_macd, direct_signal, direct_histogram = talib.MACD(
        close,
        fastperiod=12,
        slowperiod=26,
        signalperiod=9,
    )
    direct_upper, direct_middle, direct_lower = talib.BBANDS(
        close,
        timeperiod=20,
        nbdevup=2,
        nbdevdn=2,
    )

    np.testing.assert_allclose(
        ema,
        talib.EMA(close, timeperiod=14),
        equal_nan=True,
    )
    np.testing.assert_allclose(
        rsi,
        talib.RSI(close, timeperiod=14),
        equal_nan=True,
    )
    np.testing.assert_allclose(
        macd,
        np.column_stack([direct_macd, direct_signal, direct_histogram]),
        equal_nan=True,
    )
    np.testing.assert_allclose(
        bands,
        np.column_stack([direct_lower, direct_middle, direct_upper]),
        equal_nan=True,
    )


def test_ema_offset_is_applied_after_indicator(neutral_points):
    points = neutral_points["volatile"][-500:]
    context = execution_context(points)
    baseline = numeric_matrix(
        EmaSignalPlugin().compute(
            points,
            [],
            EmaSignalParams(period=14, offset=0),
            context,
        )
    )[:, 0]
    shifted = numeric_matrix(
        EmaSignalPlugin().compute(
            points,
            [],
            EmaSignalParams(period=14, offset=10),
            context,
        )
    )[:, 0]
    finite = np.isfinite(baseline)
    np.testing.assert_allclose(
        shifted[finite],
        baseline[finite] * 1.1,
    )


def test_rsi_resolves_dynamic_levels_and_regions(neutral_points):
    points = neutral_points["volatile"][-500:]
    computation = RsiSignalPlugin().compute(
        points,
        [],
        RsiSignalParams(
            period=14,
            oversold=25,
            overbought=80,
        ),
        execution_context(points),
    )
    series = computation.series[0]

    assert {item.key: item.value for item in series.reference_levels} == {
        "oversold": 25.0,
        "overbought": 80.0,
    }
    regions = {item.key: item for item in series.value_regions}
    assert regions["oversold"].upper == 25
    assert regions["neutral"].lower == 25
    assert regions["neutral"].upper == 80
    assert regions["overbought"].lower == 80


def test_macd_and_bollinger_output_shapes(neutral_points):
    points = neutral_points["volatile"][-500:]
    context = execution_context(points)
    macd = MacdSignalPlugin().compute(
        points,
        [],
        MacdSignalParams(),
        context,
    )
    bollinger = BollingerSignalPlugin().compute(
        points,
        [],
        BollingerSignalParams(),
        context,
    )

    assert [series.key for series in macd.series] == [
        "macd",
        "signal",
        "histogram",
    ]
    assert [series.kind for series in macd.series] == [
        SignalSeriesKind.LINE,
        SignalSeriesKind.LINE,
        SignalSeriesKind.BAR,
    ]
    assert isinstance(bollinger.series[0], SignalBandSeries)
    for point in bollinger.series[0].points:
        if point.lower is not None:
            assert point.lower <= point.middle <= point.upper


@pytest.mark.asyncio
@pytest.mark.parametrize("dataset_name", ["flat", "trend", "volatile", "scale_low"])
@pytest.mark.parametrize("signal_code", sorted(CORE_CODES))
async def test_core_plugins_return_ok_on_complete_datasets(
    dataset_name,
    signal_code,
    neutral_points,
):
    points = neutral_points[dataset_name]
    result = (
        await SignalService().compute(
            [
                SignalRequest(
                    instance_id=f"{signal_code}-{dataset_name}",
                    signal_code=signal_code,
                    params={},
                )
            ],
            points,
            execution_context(points),
        )
    )[0]

    assert result.status == SignalStatus.OK
    assert result.error is None
    assert all(point.date >= result.series[0].points[0].date for point in result.series[0].points)


@pytest.mark.asyncio
@pytest.mark.parametrize("signal_code", sorted(CORE_CODES))
async def test_core_plugins_are_unavailable_on_short_history(
    signal_code,
    neutral_points,
):
    plugin_class = SignalPluginRegistry.get_plugin(signal_code)
    params = plugin_class.validate_params({})
    all_points = neutral_points["volatile"]
    requirement = plugin_class.warmup_requirement(
        params,
        execution_context(all_points),
    )
    points = all_points[: max(1, requirement.minimum_points - 1)]
    context = SignalExecutionContext(
        domain=SignalDomain.ASSET,
        requested_range=DateRangeModel(
            start=points[0].date,
            end=points[-1].date,
        ),
        source_reference="asset:short",
    )

    result = (
        await SignalService().compute(
            [
                SignalRequest(
                    instance_id=signal_code,
                    signal_code=signal_code,
                    params={},
                )
            ],
            points,
            context,
        )
    )[0]

    assert result.status == SignalStatus.UNAVAILABLE


@pytest.mark.asyncio
@pytest.mark.parametrize("signal_code", sorted(CORE_CODES))
async def test_core_plugins_do_not_compact_internal_date_gaps(
    signal_code,
    neutral_points,
):
    points = neutral_points["volatile"][-500:]
    points = [point for index, point in enumerate(points) if index != 250]
    context = SignalExecutionContext(
        domain=SignalDomain.ASSET,
        requested_range=DateRangeModel(
            start=points[0].date,
            end=points[-1].date,
        ),
        source_reference="asset:gap",
    )

    result = (
        await SignalService().compute(
            [
                SignalRequest(
                    instance_id=signal_code,
                    signal_code=signal_code,
                    params={},
                )
            ],
            points,
            context,
        )
    )[0]

    assert result.status == SignalStatus.UNAVAILABLE
    assert result.availability.input_coverage.internal_gap_count == 1


@pytest.mark.parametrize(
    ("signal_code", "params"),
    [
        ("EMA", {"period": 14}),
        ("EMA", {"period": 50}),
        ("EMA", {"period": 100}),
        ("RSI", {"period": 14}),
        ("RSI", {"period": 50}),
        (
            "MACD",
            {
                "fastPeriod": 12,
                "slowPeriod": 26,
                "signalPeriod": 9,
            },
        ),
        (
            "MACD",
            {
                "fastPeriod": 20,
                "slowPeriod": 50,
                "signalPeriod": 15,
            },
        ),
        (
            "MACD",
            {
                "fastPeriod": 2,
                "slowPeriod": 5,
                "signalPeriod": 50,
            },
        ),
        ("BOLLINGER", {"period": 20}),
        ("BOLLINGER", {"period": 100}),
    ],
)
def test_warmup_formulas_hold_across_datasets(
    signal_code,
    params,
    neutral_points,
):
    plugin_class = SignalPluginRegistry.get_plugin(signal_code)
    param_model = plugin_class.validate_params(params)
    for dataset_name in (
        "trend",
        "volatile",
        "scale_low",
        "scale_high",
    ):
        full_points = neutral_points[dataset_name]
        context = execution_context(full_points)
        requirement = plugin_class.warmup_requirement(
            param_model,
            context,
        )
        truncated_points = full_points[-(VISIBLE_POINTS + requirement.total_points) :]
        reference = numeric_matrix(
            plugin_class().compute(
                full_points,
                [],
                param_model,
                context,
            )
        )[-VISIBLE_POINTS:]
        candidate = numeric_matrix(
            plugin_class().compute(
                truncated_points,
                [],
                param_model,
                context,
            )
        )[-VISIBLE_POINTS:]

        assert normalized_error(reference, candidate) <= requirement.normalized_tolerance, f"{signal_code} {params} failed on {dataset_name}"


def test_backend_outputs_converge_with_current_typescript_math(
    neutral_points,
):
    points = neutral_points["volatile"]
    values = np.asarray(
        [float(point.close) for point in points],
        dtype=float,
    )
    context = execution_context(points)

    ema = numeric_matrix(
        EmaSignalPlugin().compute(
            points,
            [],
            EmaSignalParams(period=14),
            context,
        )
    )[-VISIBLE_POINTS:, 0]
    rsi = numeric_matrix(
        RsiSignalPlugin().compute(
            points,
            [],
            RsiSignalParams(period=14),
            context,
        )
    )[-VISIBLE_POINTS:, 0]
    macd = numeric_matrix(
        MacdSignalPlugin().compute(
            points,
            [],
            MacdSignalParams(),
            context,
        )
    )[-VISIBLE_POINTS:]
    bands = numeric_matrix(
        BollingerSignalPlugin().compute(
            points,
            [],
            BollingerSignalParams(),
            context,
        )
    )[-VISIBLE_POINTS:]

    assert (
        normalized_error(
            ema[:, None],
            ts_ema(values, 14)[-VISIBLE_POINTS:, None],
        )
        <= 1e-6
    )
    assert (
        normalized_error(
            rsi[:, None],
            ts_rsi(values, 14)[-VISIBLE_POINTS:, None],
        )
        <= 1e-6
    )
    assert (
        normalized_error(
            macd,
            ts_macd(values, 12, 26, 9)[-VISIBLE_POINTS:],
        )
        <= 1e-6
    )
    assert (
        normalized_error(
            bands,
            ts_bollinger(values, 20, 2.0)[-VISIBLE_POINTS:],
        )
        <= 1e-6
    )


def test_small_fixture_is_still_valid_for_params_contract():
    points = make_signal_price_points()
    context = SignalExecutionContext(
        domain=SignalDomain.ASSET,
        requested_range=DateRangeModel(
            start=date(2026, 1, 1),
            end=date(2026, 1, 6),
        ),
        source_reference="asset:small-fixture",
    )
    assert (
        EmaSignalPlugin.warmup_requirement(
            EmaSignalParams(),
            context,
        ).minimum_points
        == 14
    )
    assert len(points) == 6
