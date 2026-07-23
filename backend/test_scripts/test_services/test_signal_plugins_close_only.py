"""Numerical and contract tests for additional close-only signal plugins."""

from __future__ import annotations

import json

import numpy as np
import pytest
import talib

from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.signals import (
    SignalDomain,
    SignalExecutionContext,
    SignalRequest,
    SignalSeriesKind,
    SignalStatus,
)
from backend.app.services.provider_registry import SignalPluginRegistry
from backend.app.services.signal_plugins import kama as kama_module
from backend.app.services.signal_plugins import ppo as ppo_module
from backend.app.services.signal_plugins import roc as roc_module
from backend.app.services.signal_plugins import sma as sma_module
from backend.app.services.signal_plugins import stoch_rsi as stoch_rsi_module
from backend.app.services.signal_plugins.kama import (
    KamaSignalParams,
    KamaSignalPlugin,
)
from backend.app.services.signal_plugins.ppo import (
    PpoSignalParams,
    PpoSignalPlugin,
)
from backend.app.services.signal_plugins.roc import (
    RocSignalParams,
    RocSignalPlugin,
)
from backend.app.services.signal_plugins.sma import (
    SmaSignalParams,
    SmaSignalPlugin,
)
from backend.app.services.signal_plugins.stoch_rsi import (
    StochRsiSignalParams,
    StochRsiSignalPlugin,
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

ADDITIONAL_CODES = {"SMA", "ROC", "STOCH_RSI", "KAMA", "PPO"}
CLOSE_ONLY_CODES = {
    "EMA",
    "SMA",
    "RSI",
    "MACD",
    "BOLLINGER",
    "ROC",
    "STOCH_RSI",
    "KAMA",
    "PPO",
}


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


def test_catalog_contains_nine_close_only_plugins():
    definitions = {item.signal_code: item for item in SignalPluginRegistry.list_definitions()}
    assert CLOSE_ONLY_CODES.issubset(definitions)
    for code in CLOSE_ONLY_CODES:
        assert definitions[code].compatible_domains == [
            SignalDomain.ASSET,
            SignalDomain.FX,
        ]
        assert definitions[code].input_requirements.price_fields == ["close"]

    stoch_properties = set(definitions["STOCH_RSI"].params_schema["properties"])
    assert stoch_properties == {
        "period",
        "dPeriod",
        "overbought",
        "oversold",
    }
    assert set(definitions["KAMA"].params_schema["properties"]) == {"period"}
    serialized = json.dumps({code: definitions[code].model_dump(mode="json") for code in ADDITIONAL_CODES})
    for ignored in ("rsi_length", "mamode", '"fast"', '"slow"'):
        assert ignored not in serialized


def test_close_only_parameter_validation_and_aliases():
    assert SmaSignalParams(period=20).period == 20
    assert RocSignalParams(period=1).period == 1
    stoch = StochRsiSignalParams.model_validate(
        {
            "period": 20,
            "dPeriod": 5,
            "overbought": 85,
            "oversold": 15,
        }
    )
    assert stoch.model_dump(mode="json", by_alias=True)["dPeriod"] == 5
    with pytest.raises(ValueError):
        StochRsiSignalParams(
            overbought=40,
            oversold=50,
        )
    assert KamaSignalParams(period=10).model_dump() == {"period": 10}
    ppo = PpoSignalParams.model_validate(
        {
            "fastPeriod": 5,
            "slowPeriod": 20,
            "signalPeriod": 7,
        }
    )
    assert ppo.model_dump(mode="json", by_alias=True) == {
        "fastPeriod": 5,
        "slowPeriod": 20,
        "signalPeriod": 7,
    }
    with pytest.raises(ValueError):
        PpoSignalParams(
            fastPeriod=20,
            slowPeriod=10,
            signalPeriod=5,
        )


@pytest.mark.parametrize(
    ("module", "function_name", "plugin_class", "params"),
    [
        (sma_module, "sma", SmaSignalPlugin, {"period": 20}),
        (roc_module, "roc", RocSignalPlugin, {"period": 12}),
        (
            stoch_rsi_module,
            "stochrsi",
            StochRsiSignalPlugin,
            {"period": 14, "dPeriod": 3},
        ),
        (kama_module, "kama", KamaSignalPlugin, {"period": 10}),
        (
            ppo_module,
            "ppo",
            PpoSignalPlugin,
            {
                "fastPeriod": 12,
                "slowPeriod": 26,
                "signalPeriod": 9,
            },
        ),
    ],
)
def test_each_close_only_plugin_requests_talib(
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
    points = neutral_points["volatile"][-1000:]
    param_model = plugin_class.validate_params(params)
    plugin_class().compute(
        points,
        [],
        param_model,
        execution_context(points),
    )

    assert calls
    assert calls[0]["talib"] is True


@pytest.mark.parametrize(
    ("talib_name", "plugin_class", "params"),
    [
        ("SMA", SmaSignalPlugin, {"period": 20}),
        ("ROC", RocSignalPlugin, {"period": 12}),
        (
            "STOCHRSI",
            StochRsiSignalPlugin,
            {"period": 14, "dPeriod": 3},
        ),
        ("KAMA", KamaSignalPlugin, {"period": 10}),
        (
            "PPO",
            PpoSignalPlugin,
            {
                "fastPeriod": 12,
                "slowPeriod": 26,
                "signalPeriod": 9,
            },
        ),
    ],
)
def test_expected_talib_function_is_actually_called(
    monkeypatch,
    talib_name,
    plugin_class,
    params,
    neutral_points,
):
    original = getattr(talib, talib_name)
    calls = 0

    def tracked(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(talib, talib_name, tracked)
    points = neutral_points["volatile"][-1000:]
    plugin_class().compute(
        points,
        [],
        plugin_class.validate_params(params),
        execution_context(points),
    )

    assert calls == 1


def test_close_only_plugins_match_direct_talib(neutral_points):
    points = neutral_points["volatile"][-1000:]
    close = np.asarray(
        [float(point.close) for point in points],
        dtype=float,
    )
    context = execution_context(points)

    sma = numeric_matrix(
        SmaSignalPlugin().compute(
            points,
            [],
            SmaSignalParams(period=20),
            context,
        )
    )[:, 0]
    roc = numeric_matrix(
        RocSignalPlugin().compute(
            points,
            [],
            RocSignalParams(period=12),
            context,
        )
    )[:, 0]
    stoch = numeric_matrix(
        StochRsiSignalPlugin().compute(
            points,
            [],
            StochRsiSignalParams(
                period=14,
                dPeriod=3,
            ),
            context,
        )
    )
    kama = numeric_matrix(
        KamaSignalPlugin().compute(
            points,
            [],
            KamaSignalParams(period=10),
            context,
        )
    )[:, 0]
    ppo = numeric_matrix(
        PpoSignalPlugin().compute(
            points,
            [],
            PpoSignalParams(),
            context,
        )
    )

    direct_k, direct_d = talib.STOCHRSI(
        close,
        timeperiod=14,
        fastk_period=14,
        fastd_period=3,
    )
    direct_ppo = talib.PPO(
        close,
        fastperiod=12,
        slowperiod=26,
    )
    np.testing.assert_allclose(
        sma,
        talib.SMA(close, timeperiod=20),
        equal_nan=True,
    )
    np.testing.assert_allclose(
        roc,
        talib.ROC(close, timeperiod=12),
        equal_nan=True,
    )
    np.testing.assert_allclose(
        stoch,
        np.column_stack([direct_k, direct_d]),
        equal_nan=True,
    )
    np.testing.assert_allclose(
        kama,
        talib.KAMA(close, timeperiod=10),
        equal_nan=True,
    )
    np.testing.assert_allclose(
        ppo[:, 0],
        direct_ppo,
        equal_nan=True,
    )
    finite = np.isfinite(ppo[:, 1]) & np.isfinite(ppo[:, 2])
    np.testing.assert_allclose(
        ppo[finite, 2],
        ppo[finite, 0] - ppo[finite, 1],
    )


def test_composite_shapes_and_dynamic_levels(neutral_points):
    points = neutral_points["volatile"][-1000:]
    context = execution_context(points)
    stoch = StochRsiSignalPlugin().compute(
        points,
        [],
        StochRsiSignalParams(
            period=14,
            dPeriod=3,
            oversold=15,
            overbought=85,
        ),
        context,
    )
    ppo = PpoSignalPlugin().compute(
        points,
        [],
        PpoSignalParams(),
        context,
    )
    roc = RocSignalPlugin().compute(
        points,
        [],
        RocSignalParams(),
        context,
    )

    assert [series.key for series in stoch.series] == ["k", "d"]
    assert {level.key: level.value for level in stoch.series[0].reference_levels} == {
        "oversold": 15.0,
        "overbought": 85.0,
    }
    assert stoch.series[1].reference_levels == []
    assert [series.key for series in ppo.series] == [
        "ppo",
        "signal",
        "histogram",
    ]
    assert [series.kind for series in ppo.series] == [
        SignalSeriesKind.LINE,
        SignalSeriesKind.LINE,
        SignalSeriesKind.BAR,
    ]
    assert ppo.series[0].reference_levels[0].value == 0
    assert roc.series[0].reference_levels[0].value == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("dataset_name", ["flat", "trend", "volatile", "scale_low"])
@pytest.mark.parametrize("signal_code", sorted(ADDITIONAL_CODES))
async def test_close_only_plugins_return_ok_on_complete_datasets(
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


@pytest.mark.asyncio
@pytest.mark.parametrize("signal_code", sorted(ADDITIONAL_CODES))
async def test_close_only_plugins_are_unavailable_on_short_history(
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
        source_reference="asset:short-close-only",
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
async def test_kama_nondefault_minimum_boundary_is_not_failed(
    neutral_points,
):
    all_points = neutral_points["volatile"]
    params = KamaSignalParams(period=50)
    requirement = KamaSignalPlugin.warmup_requirement(
        params,
        execution_context(all_points),
    )
    assert requirement.minimum_points == 51

    short_points = all_points[:50]
    short_context = SignalExecutionContext(
        domain=SignalDomain.ASSET,
        requested_range=DateRangeModel(
            start=short_points[0].date,
            end=short_points[-1].date,
        ),
        source_reference="asset:kama-short",
    )
    short_result = (
        await SignalService().compute(
            [
                SignalRequest(
                    instance_id="kama-short",
                    signal_code="KAMA",
                    params={"period": 50},
                )
            ],
            short_points,
            short_context,
        )
    )[0]

    boundary_points = all_points[:51]
    boundary_context = SignalExecutionContext(
        domain=SignalDomain.ASSET,
        requested_range=DateRangeModel(
            start=boundary_points[0].date,
            end=boundary_points[-1].date,
        ),
        source_reference="asset:kama-boundary",
    )
    boundary_result = (
        await SignalService().compute(
            [
                SignalRequest(
                    instance_id="kama-boundary",
                    signal_code="KAMA",
                    params={"period": 50},
                )
            ],
            boundary_points,
            boundary_context,
        )
    )[0]

    assert short_result.status == SignalStatus.UNAVAILABLE
    assert boundary_result.status == SignalStatus.PARTIAL
    assert boundary_result.error is None


@pytest.mark.asyncio
@pytest.mark.parametrize("signal_code", sorted(ADDITIONAL_CODES))
async def test_close_only_plugins_reject_internal_date_gaps(
    signal_code,
    neutral_points,
):
    points = neutral_points["volatile"][-1000:]
    points = [point for index, point in enumerate(points) if index != 500]
    context = SignalExecutionContext(
        domain=SignalDomain.ASSET,
        requested_range=DateRangeModel(
            start=points[0].date,
            end=points[-1].date,
        ),
        source_reference="asset:gap-close-only",
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
        ("SMA", {"period": 20}),
        ("SMA", {"period": 100}),
        ("ROC", {"period": 12}),
        ("ROC", {"period": 50}),
        ("STOCH_RSI", {"period": 14, "dPeriod": 3}),
        ("STOCH_RSI", {"period": 50, "dPeriod": 10}),
        ("KAMA", {"period": 10}),
        ("KAMA", {"period": 50}),
        ("KAMA", {"period": 100}),
        (
            "PPO",
            {
                "fastPeriod": 12,
                "slowPeriod": 26,
                "signalPeriod": 9,
            },
        ),
        (
            "PPO",
            {
                "fastPeriod": 2,
                "slowPeriod": 5,
                "signalPeriod": 50,
            },
        ),
        (
            "PPO",
            {
                "fastPeriod": 50,
                "slowPeriod": 200,
                "signalPeriod": 100,
            },
        ),
    ],
)
def test_close_only_warmup_formulas_hold(
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


@pytest.mark.asyncio
@pytest.mark.parametrize("signal_code", sorted(ADDITIONAL_CODES))
async def test_close_only_asset_fx_parity(
    signal_code,
    neutral_points,
):
    points = neutral_points["volatile"]
    request = SignalRequest(
        instance_id=signal_code,
        signal_code=signal_code,
        params={},
    )
    asset = (
        await SignalService().compute(
            [request],
            points,
            execution_context(
                points,
                domain=SignalDomain.ASSET,
            ),
        )
    )[0]
    fx = (
        await SignalService().compute(
            [request],
            points,
            execution_context(
                points,
                domain=SignalDomain.FX,
            ),
        )
    )[0]

    assert asset.status == SignalStatus.OK
    assert fx.status == SignalStatus.OK
    assert asset.series == fx.series
