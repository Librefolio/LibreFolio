"""Numerical and availability tests for OBV and MFI plugins."""

from __future__ import annotations

from decimal import Decimal

import numpy as np
import pytest
import talib

from backend.app.schemas.common import BackwardFillInfo, DateRangeModel
from backend.app.schemas.signals import (
    SignalAvailabilityReason,
    SignalDomain,
    SignalExecutionContext,
    SignalRequest,
    SignalSourceCapability,
    SignalStatus,
    SignalVolumeKind,
)
from backend.app.services.provider_registry import SignalPluginRegistry
from backend.app.services.signal_plugins import mfi as mfi_module
from backend.app.services.signal_plugins import obv as obv_module
from backend.app.services.signal_plugins.base import SignalUnavailableError
from backend.app.services.signal_plugins.mfi import (
    MfiSignalParams,
    MfiSignalPlugin,
)
from backend.app.services.signal_plugins.obv import (
    ObvSignalParams,
    ObvSignalPlugin,
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

VOLUME_CODES = {"OBV", "MFI"}


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


def test_volume_catalog_includes_technical_and_risk_plugins():
    definitions = {item.signal_code: item for item in SignalPluginRegistry.list_definitions()}
    assert len(definitions) == 22
    assert VOLUME_CODES.issubset(definitions)
    assert definitions["OBV"].input_requirements.price_fields == [
        "close",
        "volume",
    ]
    assert definitions["MFI"].input_requirements.price_fields == [
        "high",
        "low",
        "close",
        "volume",
    ]
    assert definitions["OBV"].compatible_domains == [SignalDomain.ASSET]
    assert definitions["MFI"].compatible_domains == [SignalDomain.ASSET]


def test_volume_parameter_validation_and_levels():
    assert ObvSignalParams().model_dump() == {}
    assert MfiSignalParams(period=14).period == 14
    with pytest.raises(ValueError):
        MfiSignalParams(period=1)
    with pytest.raises(ValueError):
        MfiSignalParams(oversold=60, overbought=50)


@pytest.mark.parametrize(
    ("module", "function_name", "plugin_class"),
    [
        (obv_module, "obv", ObvSignalPlugin),
        (mfi_module, "mfi", MfiSignalPlugin),
    ],
)
def test_volume_plugins_request_talib(
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
    points = neutral_points["volatile"][-1000:]
    plugin_class().compute(
        points,
        [],
        plugin_class.validate_params({}),
        execution_context(points),
    )

    assert calls
    assert calls[0]["talib"] is True


@pytest.mark.parametrize(
    ("plugin_class", "talib_name"),
    [
        (ObvSignalPlugin, "OBV"),
        (MfiSignalPlugin, "MFI"),
    ],
)
def test_volume_talib_function_is_actually_called(
    monkeypatch,
    plugin_class,
    talib_name,
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
        plugin_class.validate_params({}),
        execution_context(points),
    )

    assert calls == 1


def test_obv_rebases_at_requested_start_and_mfi_matches_talib(
    neutral_points,
):
    points = neutral_points["volatile"][-1000:]
    context = execution_context(points)
    close = np.asarray(
        [float(point.close) for point in points],
        dtype=float,
    )
    high = np.asarray(
        [float(point.high) for point in points],
        dtype=float,
    )
    low = np.asarray(
        [float(point.low) for point in points],
        dtype=float,
    )
    volume = np.asarray(
        [float(point.volume) for point in points],
        dtype=float,
    )
    obv = numeric_matrix(
        ObvSignalPlugin().compute(
            points,
            [],
            ObvSignalParams(),
            context,
        )
    )[:, 0]
    mfi = numeric_matrix(
        MfiSignalPlugin().compute(
            points,
            [],
            MfiSignalParams(),
            context,
        )
    )[:, 0]
    direct_obv = talib.OBV(close, volume)
    baseline_index = len(points) - VISIBLE_POINTS

    np.testing.assert_allclose(
        obv,
        direct_obv - direct_obv[baseline_index],
        equal_nan=True,
    )
    assert obv[baseline_index] == 0
    np.testing.assert_allclose(
        mfi,
        talib.MFI(
            high,
            low,
            close,
            volume,
            timeperiod=14,
        ),
        equal_nan=True,
    )


def test_mfi_dynamic_levels_and_regions(neutral_points):
    points = neutral_points["volatile"][-1000:]
    computation = MfiSignalPlugin().compute(
        points,
        [],
        MfiSignalParams(
            period=14,
            oversold=15,
            overbought=85,
        ),
        execution_context(points),
    )
    series = computation.series[0]

    assert {level.key: level.value for level in series.reference_levels} == {
        "oversold": 15.0,
        "overbought": 85.0,
    }
    regions = {region.key: region for region in series.value_regions}
    assert regions["neutral"].lower == 15
    assert regions["neutral"].upper == 85


@pytest.mark.asyncio
@pytest.mark.parametrize("dataset_name", ["flat", "trend", "volatile", "scale_low"])
@pytest.mark.parametrize("signal_code", sorted(VOLUME_CODES))
async def test_volume_plugins_return_ok_on_complete_data(
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
@pytest.mark.parametrize("signal_code", sorted(VOLUME_CODES))
async def test_zero_volume_is_valid_not_missing(
    signal_code,
    neutral_points,
):
    points = [point.model_copy(update={"volume": 0}) for point in neutral_points["volatile"]]
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

    assert result.status == SignalStatus.OK
    assert all(point.value == 0 for point in result.series[0].points)


@pytest.mark.asyncio
@pytest.mark.parametrize("signal_code", sorted(VOLUME_CODES))
async def test_missing_volume_is_unavailable(
    signal_code,
    neutral_points,
):
    points = [point.model_copy(update={"volume": None}) for point in neutral_points["volatile"]]
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


@pytest.mark.asyncio
@pytest.mark.parametrize("signal_code", sorted(VOLUME_CODES))
async def test_partial_volume_uses_latest_contiguous_segment(
    signal_code,
    neutral_points,
):
    points = neutral_points["volatile"][-1000:].copy()
    points[500] = points[500].model_copy(update={"volume": None})
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

    assert result.status == SignalStatus.PARTIAL
    assert result.availability.reason_code == SignalAvailabilityReason.PARTIAL_INPUT_COVERAGE
    assert result.availability.input_coverage.internal_gap_count == 1
    gap_date = points[500].date
    assert all(point.date > gap_date for series in result.series for point in series.points)


@pytest.mark.asyncio
@pytest.mark.parametrize("signal_code", sorted(VOLUME_CODES))
async def test_volume_plugins_are_unavailable_for_fx(
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


@pytest.mark.parametrize(
    ("signal_code", "params"),
    [
        ("OBV", {}),
        ("MFI", {"period": 14}),
        ("MFI", {"period": 50}),
        ("MFI", {"period": 200}),
    ],
)
def test_volume_warmup_formulas_hold(
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

        assert normalized_error(reference, candidate) <= requirement.normalized_tolerance


@pytest.mark.asyncio
@pytest.mark.parametrize("signal_code", ["MFI"])
async def test_volume_plugins_are_unavailable_on_short_history(
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
        source_reference="asset:short-volume",
        source_capability=SignalSourceCapability(
            supports_meaningful_volume=True,
            volume_kind=SignalVolumeKind.TRADED_SHARES,
        ),
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
async def test_obv_single_point_is_partial_not_unavailable(
    neutral_points,
):
    point = neutral_points["volatile"][:1]
    context = SignalExecutionContext(
        domain=SignalDomain.ASSET,
        requested_range=DateRangeModel(
            start=point[0].date,
            end=point[0].date,
        ),
        source_reference="asset:obv-single",
        source_capability=SignalSourceCapability(
            supports_meaningful_volume=True,
            volume_kind=SignalVolumeKind.TRADED_SHARES,
        ),
    )
    result = (
        await SignalService().compute(
            [
                SignalRequest(
                    instance_id="OBV",
                    signal_code="OBV",
                    params={},
                )
            ],
            point,
            context,
        )
    )[0]

    assert result.status == SignalStatus.PARTIAL
    assert result.series[0].points[0].value == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("signal_code", ["MFI", "OBV"])
async def test_volume_plugins_are_unavailable_for_unknown_source_capability(
    signal_code,
    neutral_points,
):
    """A source that hasn't declared meaningful-volume support (the default,
    e.g. mixed/unregistered/manual sources) must gate MFI/OBV closed with a
    distinct MISSING_SOURCE_CAPABILITY reason — never silently compute."""
    points = neutral_points["volatile"][-1000:]
    context = SignalExecutionContext(
        domain=SignalDomain.ASSET,
        requested_range=DateRangeModel(
            start=points[-VISIBLE_POINTS].date,
            end=points[-1].date,
        ),
        source_reference="asset:unknown-source",
        # source_capability omitted -> defaults to unsupported/unknown.
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
    assert result.availability.reason_code == SignalAvailabilityReason.MISSING_SOURCE_CAPABILITY


@pytest.mark.parametrize("plugin_class", [MfiSignalPlugin, ObvSignalPlugin])
def test_volume_plugins_reject_negative_volume(plugin_class, neutral_points):
    """Negative volume is structurally invalid even though the schema's
    finiteness check alone would let it through."""
    points = neutral_points["volatile"][-30:]
    tampered = list(points)
    tampered[-1] = tampered[-1].model_copy(update={"volume": Decimal("-1")})

    with pytest.raises(SignalUnavailableError, match="non-negative"):
        plugin_class.validate_input(tampered, [], plugin_class.validate_params({}), execution_context(points))


@pytest.mark.parametrize("plugin_class", [MfiSignalPlugin, ObvSignalPlugin])
def test_volume_plugins_reject_sparse_directly_observed_volume(plugin_class, neutral_points):
    """Volume that is mostly backward-filled (stale, not fresh evidence)
    fails the plugin's own observed-coverage check even when every point has
    a non-null value."""
    points = neutral_points["volatile"][-30:]
    stale_fill = BackwardFillInfo(actual_rate_date=points[0].date, days_back=1)
    tampered = [point.model_copy(update={"backward_fill_info": stale_fill}) for point in points[:-1]] + [points[-1]]

    with pytest.raises(SignalUnavailableError, match="insufficient directly observed volume"):
        plugin_class.validate_input(tampered, [], plugin_class.validate_params({}), execution_context(points))


@pytest.mark.parametrize("plugin_class", [MfiSignalPlugin, ObvSignalPlugin])
def test_volume_plugins_reject_non_increasing_dates(plugin_class, neutral_points):
    """Defense-in-depth: selection logic must never hand the plugin
    non-strictly-increasing dates."""
    points = neutral_points["volatile"][-30:]
    tampered = list(points)
    tampered[-1] = tampered[-1].model_copy(update={"date": tampered[-2].date})

    with pytest.raises(SignalUnavailableError, match="strictly increasing"):
        plugin_class.validate_input(tampered, [], plugin_class.validate_params({}), execution_context(points))


@pytest.mark.parametrize("plugin_class", [MfiSignalPlugin, ObvSignalPlugin])
def test_volume_plugins_accept_sufficient_observed_volume(plugin_class, neutral_points):
    """Sanity check: well-formed, fully-observed volume passes validate_input
    without raising (positive-path complement to the rejection tests above)."""
    points = neutral_points["volatile"][-30:]
    assert plugin_class.validate_input(points, [], plugin_class.validate_params({}), execution_context(points)) is None
