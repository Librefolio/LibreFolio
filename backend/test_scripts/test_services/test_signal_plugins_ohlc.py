"""Numerical and availability tests for OHLC signal plugins."""

from __future__ import annotations

import inspect

import numpy as np
import pandas as pd
import pytest
import talib

from backend.app.schemas.signals import (
    SignalAvailabilityReason,
    SignalDomain,
    SignalRequest,
    SignalSeriesKind,
    SignalStatus,
)
from backend.app.services.provider_registry import SignalPluginRegistry
from backend.app.services.signal_plugins import adx as adx_module
from backend.app.services.signal_plugins import aroon as aroon_module
from backend.app.services.signal_plugins import atr as atr_module
from backend.app.services.signal_plugins import cci as cci_module
from backend.app.services.signal_plugins import donchian as donchian_module
from backend.app.services.signal_plugins import natr as natr_module
from backend.app.services.signal_plugins.adx import (
    AdxSignalParams,
    AdxSignalPlugin,
)
from backend.app.services.signal_plugins.aroon import (
    AroonSignalParams,
    AroonSignalPlugin,
)
from backend.app.services.signal_plugins.atr import (
    AtrSignalParams,
    AtrSignalPlugin,
)
from backend.app.services.signal_plugins.cci import (
    CciSignalParams,
    CciSignalPlugin,
)
from backend.app.services.signal_plugins.donchian import (
    DonchianSignalParams,
    DonchianSignalPlugin,
)
from backend.app.services.signal_plugins.natr import (
    NatrSignalParams,
    NatrSignalPlugin,
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

OHLC_CODES = {"ATR", "ADX", "NATR", "AROON", "DONCHIAN", "CCI"}


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


def test_ohlc_catalog_and_input_requirements():
    definitions = {item.signal_code: item for item in SignalPluginRegistry.list_definitions()}
    assert OHLC_CODES.issubset(definitions)
    assert definitions["AROON"].input_requirements.price_fields == [
        "high",
        "low",
    ]
    assert definitions["DONCHIAN"].input_requirements.price_fields == [
        "high",
        "low",
    ]
    for code in {"ATR", "ADX", "NATR", "CCI"}:
        assert definitions[code].input_requirements.price_fields == [
            "high",
            "low",
            "close",
        ]
    for code in OHLC_CODES:
        assert definitions[code].compatible_domains == [SignalDomain.ASSET]


def test_ohlc_parameter_validation():
    assert AtrSignalParams(period=14).period == 14
    assert AdxSignalParams(period=14).period == 14
    assert NatrSignalParams(period=14).period == 14
    assert AroonSignalParams(period=14).period == 14
    assert DonchianSignalParams(period=20).period == 20
    assert CciSignalParams(period=14).period == 14
    for params_type in (
        AtrSignalParams,
        AdxSignalParams,
        NatrSignalParams,
        AroonSignalParams,
        DonchianSignalParams,
        CciSignalParams,
    ):
        with pytest.raises(ValueError):
            params_type(period=1)


@pytest.mark.parametrize(
    ("module", "function_name", "plugin_class"),
    [
        (atr_module, "atr", AtrSignalPlugin),
        (adx_module, "adx", AdxSignalPlugin),
        (natr_module, "natr", NatrSignalPlugin),
        (aroon_module, "aroon", AroonSignalPlugin),
        (cci_module, "cci", CciSignalPlugin),
    ],
)
def test_delegated_ohlc_plugins_request_talib(
    monkeypatch,
    module,
    function_name,
    plugin_class,
    neutral_points,
):
    original = getattr(module.ta, function_name)
    calls: list[dict] = []

    def tracked(*args, **kwargs):
        calls.append(kwargs.copy())
        return original(*args, **kwargs)

    monkeypatch.setattr(module.ta, function_name, tracked)
    points = neutral_points["volatile"][-2000:]
    params = plugin_class.validate_params({})
    plugin_class().compute(
        points,
        [],
        params,
        execution_context(points),
    )

    assert calls
    assert calls[0]["talib"] is True


@pytest.mark.parametrize(
    ("plugin_class", "talib_names"),
    [
        (AtrSignalPlugin, ("ATR",)),
        (AdxSignalPlugin, ("ADX", "PLUS_DI", "MINUS_DI")),
        (NatrSignalPlugin, ("NATR",)),
        (AroonSignalPlugin, ("AROON", "AROONOSC")),
        (CciSignalPlugin, ("CCI",)),
    ],
)
def test_expected_ohlc_talib_functions_are_called(
    monkeypatch,
    plugin_class,
    talib_names,
    neutral_points,
):
    calls = dict.fromkeys(talib_names, 0)
    for name in talib_names:
        original = getattr(talib, name)

        def tracked(
            *args,
            _name=name,
            _original=original,
            **kwargs,
        ):
            calls[_name] += 1
            return _original(*args, **kwargs)

        monkeypatch.setattr(talib, name, tracked)

    points = neutral_points["volatile"][-2000:]
    plugin_class().compute(
        points,
        [],
        plugin_class.validate_params({}),
        execution_context(points),
    )

    assert all(count == 1 for count in calls.values())


def test_donchian_is_native_and_does_not_accept_talib(
    monkeypatch,
    neutral_points,
):
    original = donchian_module.ta.donchian
    calls: list[dict] = []

    def tracked(*args, **kwargs):
        calls.append(kwargs.copy())
        return original(*args, **kwargs)

    monkeypatch.setattr(
        donchian_module.ta,
        "donchian",
        tracked,
    )
    points = neutral_points["volatile"][-500:]
    DonchianSignalPlugin().compute(
        points,
        [],
        DonchianSignalParams(),
        execution_context(points),
    )

    assert calls
    assert "talib" not in calls[0]
    assert "talib" not in inspect.getsource(donchian_module.DonchianSignalPlugin.compute)


def test_ohlc_plugins_match_direct_references(neutral_points):
    points = neutral_points["volatile"][-2000:]
    high = np.asarray(
        [float(point.high) for point in points],
        dtype=float,
    )
    low = np.asarray(
        [float(point.low) for point in points],
        dtype=float,
    )
    close = np.asarray(
        [float(point.close) for point in points],
        dtype=float,
    )
    context = execution_context(points)

    atr = numeric_matrix(
        AtrSignalPlugin().compute(
            points,
            [],
            AtrSignalParams(),
            context,
        )
    )[:, 0]
    adx = numeric_matrix(
        AdxSignalPlugin().compute(
            points,
            [],
            AdxSignalParams(),
            context,
        )
    )
    natr = numeric_matrix(
        NatrSignalPlugin().compute(
            points,
            [],
            NatrSignalParams(),
            context,
        )
    )[:, 0]
    aroon = numeric_matrix(
        AroonSignalPlugin().compute(
            points,
            [],
            AroonSignalParams(),
            context,
        )
    )
    cci = numeric_matrix(
        CciSignalPlugin().compute(
            points,
            [],
            CciSignalParams(),
            context,
        )
    )[:, 0]
    donchian = numeric_matrix(
        DonchianSignalPlugin().compute(
            points,
            [],
            DonchianSignalParams(),
            context,
        )
    )

    direct_down, direct_up = talib.AROON(
        high,
        low,
        timeperiod=14,
    )
    np.testing.assert_allclose(
        atr,
        talib.ATR(high, low, close, timeperiod=14),
        equal_nan=True,
    )
    np.testing.assert_allclose(
        adx,
        np.column_stack(
            [
                talib.ADX(high, low, close, timeperiod=14),
                talib.PLUS_DI(
                    high,
                    low,
                    close,
                    timeperiod=14,
                ),
                talib.MINUS_DI(
                    high,
                    low,
                    close,
                    timeperiod=14,
                ),
            ]
        ),
        equal_nan=True,
    )
    np.testing.assert_allclose(
        natr,
        talib.NATR(high, low, close, timeperiod=14),
        equal_nan=True,
    )
    np.testing.assert_allclose(
        aroon,
        np.column_stack(
            [
                direct_up,
                direct_down,
                talib.AROONOSC(
                    high,
                    low,
                    timeperiod=14,
                ),
            ]
        ),
        equal_nan=True,
    )
    np.testing.assert_allclose(
        cci,
        talib.CCI(high, low, close, timeperiod=14),
        equal_nan=True,
    )
    high_series = pd.Series(high)
    low_series = pd.Series(low)
    lower = low_series.rolling(20).min().to_numpy()
    upper = high_series.rolling(20).max().to_numpy()
    np.testing.assert_allclose(
        donchian,
        np.column_stack([lower, 0.5 * (lower + upper), upper]),
        equal_nan=True,
    )


def test_ohlc_composite_shapes_and_levels(neutral_points):
    points = neutral_points["volatile"][-2000:]
    context = execution_context(points)
    adx = AdxSignalPlugin().compute(
        points,
        [],
        AdxSignalParams(),
        context,
    )
    aroon = AroonSignalPlugin().compute(
        points,
        [],
        AroonSignalParams(),
        context,
    )
    donchian = DonchianSignalPlugin().compute(
        points,
        [],
        DonchianSignalParams(),
        context,
    )
    cci = CciSignalPlugin().compute(
        points,
        [],
        CciSignalParams(),
        context,
    )

    assert [series.key for series in adx.series] == [
        "adx",
        "plus_di",
        "minus_di",
    ]
    assert [series.key for series in aroon.series] == [
        "up",
        "down",
        "oscillator",
    ]
    assert aroon.series[2].reference_levels[0].value == 0
    assert donchian.series[0].kind == SignalSeriesKind.BAND
    assert {level.value for level in cci.series[0].reference_levels} == {-100.0, 0.0, 100.0}


@pytest.mark.asyncio
@pytest.mark.parametrize("dataset_name", ["flat", "trend", "volatile", "scale_low"])
@pytest.mark.parametrize("signal_code", sorted(OHLC_CODES))
async def test_ohlc_plugins_return_ok_on_complete_data(
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


@pytest.mark.asyncio
@pytest.mark.parametrize("signal_code", sorted(OHLC_CODES))
async def test_ohlc_plugins_are_statically_unavailable_for_fx(
    signal_code,
    neutral_points,
):
    points = neutral_points["volatile"]
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
            execution_context(
                points,
                domain=SignalDomain.FX,
            ),
        )
    )[0]

    assert result.status == SignalStatus.UNAVAILABLE
    assert result.availability.reason_code == SignalAvailabilityReason.INCOMPATIBLE_DOMAIN


@pytest.mark.asyncio
@pytest.mark.parametrize("signal_code", sorted(OHLC_CODES))
async def test_missing_required_ohlc_field_is_unavailable(
    signal_code,
    neutral_points,
):
    plugin_class = SignalPluginRegistry.get_plugin(signal_code)
    missing_field = plugin_class.input_requirements.price_fields[0]
    points = [point.model_copy(update={missing_field.value: None}) for point in neutral_points["volatile"]]
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
            execution_context(points),
        )
    )[0]

    assert result.status == SignalStatus.UNAVAILABLE
    assert result.availability.reason_code == SignalAvailabilityReason.MISSING_INPUT_FIELDS
    assert missing_field in result.availability.missing_price_fields


@pytest.mark.asyncio
@pytest.mark.parametrize("signal_code", sorted(OHLC_CODES))
async def test_partial_ohlc_field_is_not_compacted(
    signal_code,
    neutral_points,
):
    plugin_class = SignalPluginRegistry.get_plugin(signal_code)
    missing_field = plugin_class.input_requirements.price_fields[0]
    points = neutral_points["volatile"][-2000:].copy()
    points[1000] = points[1000].model_copy(update={missing_field.value: None})
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
            execution_context(points),
        )
    )[0]

    assert result.status == SignalStatus.UNAVAILABLE
    assert result.availability.reason_code == SignalAvailabilityReason.INSUFFICIENT_INPUT_COVERAGE
    assert result.availability.input_coverage.internal_gap_count == 1


@pytest.mark.parametrize(
    ("signal_code", "params"),
    [
        ("ATR", {"period": 14}),
        ("ATR", {"period": 50}),
        ("ATR", {"period": 100}),
        ("NATR", {"period": 14}),
        ("NATR", {"period": 50}),
        ("NATR", {"period": 100}),
        ("ADX", {"period": 14}),
        ("ADX", {"period": 50}),
        ("ADX", {"period": 95}),
        ("ADX", {"period": 100}),
        ("ADX", {"period": 150}),
        ("ADX", {"period": 200}),
        ("AROON", {"period": 14}),
        ("AROON", {"period": 50}),
        ("DONCHIAN", {"period": 20}),
        ("DONCHIAN", {"period": 100}),
        ("CCI", {"period": 14}),
        ("CCI", {"period": 50}),
    ],
)
def test_ohlc_warmup_formulas_hold(
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
