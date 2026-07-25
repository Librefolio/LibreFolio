"""Uniform regression matrix for all production signal plugins."""

from __future__ import annotations

import inspect
import json
from datetime import timedelta
from pathlib import Path

import pytest

from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.signals import (
    SignalAvailabilityReason,
    SignalCadence,
    SignalDataPolicy,
    SignalDomain,
    SignalErrorCode,
    SignalExecutionContext,
    SignalPriceField,
    SignalRequest,
    SignalStatus,
    SignalWarningCode,
)
from backend.app.services.provider_registry import SignalPluginRegistry
from backend.app.services.signal_service import SignalService
from backend.test_scripts.fixtures.signals.plugin_test_utils import (
    VISIBLE_POINTS,
    execution_context,
    frame_to_points,
    load_signal_frames,
)

EXPECTED_CODES = {
    "EMA",
    "SMA",
    "RSI",
    "MACD",
    "BOLLINGER",
    "ROC",
    "STOCH_RSI",
    "KAMA",
    "PPO",
    "ATR",
    "ADX",
    "NATR",
    "AROON",
    "DONCHIAN",
    "CCI",
    "OBV",
    "MFI",
}
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
PARTIAL_CONTIGUOUS_CODES = {
    "ADX",
    "AROON",
    "ATR",
    "CCI",
    "DONCHIAN",
    "MFI",
    "NATR",
    "OBV",
}


@pytest.fixture(scope="module")
def frames():
    return load_signal_frames(
        (
            "flat",
            "trend",
            "volatile",
            "scale_low",
        )
    )


@pytest.fixture(scope="module")
def neutral_points(frames):
    return {name: frame_to_points(frame) for name, frame in frames.items()}


def default_requests() -> list[SignalRequest]:
    return [
        SignalRequest(
            instance_id=code.lower(),
            signal_code=code,
            params={},
        )
        for code in sorted(EXPECTED_CODES)
    ]


def test_registry_has_exactly_seventeen_complete_definitions():
    definitions = SignalPluginRegistry.list_definitions()
    assert {definition.signal_code for definition in definitions} == EXPECTED_CODES
    assert len(definitions) == 17

    for definition in definitions:
        assert definition.implementation_version
        assert definition.docs_path
        documentation = Path("mkdocs_src/docs") / f"{definition.docs_path.rstrip('/')}.en.md"
        assert documentation.is_file()
        assert definition.params_schema["additionalProperties"] is False
        assert definition.output_specs
        assert len({spec.key for spec in definition.output_specs}) == len(definition.output_specs)
        plugin_class = SignalPluginRegistry.get_plugin(definition.signal_code)
        normalized_defaults = plugin_class.validate_params(definition.default_params).model_dump(mode="json", by_alias=True)
        assert normalized_defaults == definition.default_params

    serialized = json.dumps([definition.model_dump(mode="json") for definition in definitions])
    for forbidden in (
        "pandas_ta",
        "talib",
        "lineWidth",
        "lineType",
        '"color"',
    ):
        assert forbidden not in serialized


def test_backend_path_is_sixteen_delegated_plus_native_donchian():
    for code in EXPECTED_CODES:
        plugin_class = SignalPluginRegistry.get_plugin(code)
        source = inspect.getsource(plugin_class.compute)
        if code == "DONCHIAN":
            assert "talib=True" not in source
        else:
            assert "talib=True" in source


def test_asset_only_field_rich_plugins_allow_partial_contiguous_input():
    for code in EXPECTED_CODES:
        requirements = SignalPluginRegistry.get_plugin(code).input_requirements
        if code in PARTIAL_CONTIGUOUS_CODES:
            assert requirements.data_policy == SignalDataPolicy.ALLOW_PARTIAL_CONTIGUOUS
            assert requirements.minimum_coverage == 0.5
        else:
            assert requirements.data_policy == SignalDataPolicy.STRICT_CONTIGUOUS
            assert requirements.minimum_coverage == 1.0


def test_full_plan_aggregates_all_fields_and_max_warmup(neutral_points):
    points = neutral_points["volatile"]
    plan = SignalService().prepare_plan(
        default_requests(),
        execution_context(points),
    )

    assert plan.unique_computation_count == 17
    assert plan.required_price_fields == frozenset(
        {
            SignalPriceField.HIGH,
            SignalPriceField.LOW,
            SignalPriceField.CLOSE,
            SignalPriceField.VOLUME,
        }
    )
    assert plan.requires_events is False
    assert plan.max_history_points_before_visible == 18 * 14


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "dataset_name",
    ["flat", "trend", "volatile", "scale_low"],
)
async def test_all_seventeen_plugins_batch_ok_on_asset(
    dataset_name,
    neutral_points,
):
    points = neutral_points[dataset_name]
    results = await SignalService().compute(
        default_requests(),
        points,
        execution_context(points),
    )

    assert len(results) == 17
    assert all(result.status == SignalStatus.OK for result in results)
    for result in results:
        plugin_class = SignalPluginRegistry.get_plugin(result.signal_code)
        assert [series.key for series in result.series] == [spec.key for spec in plugin_class.output_specs]
        assert [series.kind for series in result.series] == [spec.kind for spec in plugin_class.output_specs]
        assert [series.style for series in result.series] == [spec.style for spec in plugin_class.output_specs]
        assert [series.description_key for series in result.series] == [spec.description_key for spec in plugin_class.output_specs]
        assert all(len(series.points) == VISIBLE_POINTS for series in result.series)
        assert result.model_dump_json()


@pytest.mark.asyncio
async def test_fx_batch_exposes_only_nine_close_only_plugins(
    neutral_points,
):
    points = neutral_points["volatile"]
    results = await SignalService().compute(
        default_requests(),
        points,
        execution_context(
            points,
            domain=SignalDomain.FX,
        ),
    )
    by_code = {result.signal_code: result for result in results}

    assert {code for code, result in by_code.items() if result.status == SignalStatus.OK} == CLOSE_ONLY_CODES
    for code in EXPECTED_CODES - CLOSE_ONLY_CODES:
        assert by_code[code].status == SignalStatus.UNAVAILABLE
        assert by_code[code].availability.reason_code == SignalAvailabilityReason.INCOMPATIBLE_DOMAIN


@pytest.mark.asyncio
@pytest.mark.parametrize("signal_code", sorted(EXPECTED_CODES))
async def test_exact_minimum_history_is_partial_not_failed(
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
    points = all_points[: requirement.minimum_points]
    context = SignalExecutionContext(
        domain=SignalDomain.ASSET,
        requested_range=DateRangeModel(
            start=points[0].date,
            end=points[-1].date,
        ),
        source_reference=f"asset:minimum:{signal_code}",
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

    assert result.status == SignalStatus.PARTIAL
    assert result.error is None
    assert any(warning.code == SignalWarningCode.INCOMPLETE_WARMUP for warning in result.warnings)


@pytest.mark.asyncio
@pytest.mark.parametrize("signal_code", sorted(EXPECTED_CODES))
async def test_every_required_field_is_dynamically_enforced(
    signal_code,
    neutral_points,
):
    plugin_class = SignalPluginRegistry.get_plugin(signal_code)
    base_points = neutral_points["volatile"]

    for field in plugin_class.input_requirements.price_fields:
        points = [point.model_copy(update={field.value: None}) for point in base_points]
        result = (
            await SignalService().compute(
                [
                    SignalRequest(
                        instance_id=f"{signal_code}-{field.value}",
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
        assert field in result.availability.missing_price_fields


@pytest.mark.asyncio
@pytest.mark.parametrize("signal_code", sorted(EXPECTED_CODES))
async def test_partial_required_field_never_compacts_dates(
    signal_code,
    neutral_points,
):
    plugin_class = SignalPluginRegistry.get_plugin(signal_code)
    field = plugin_class.input_requirements.price_fields[0]
    points = neutral_points["volatile"][-1000:].copy()
    points[500] = points[500].model_copy(update={field.value: None})
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

    if signal_code in PARTIAL_CONTIGUOUS_CODES:
        assert result.status == SignalStatus.PARTIAL
        assert result.availability.reason_code == SignalAvailabilityReason.PARTIAL_INPUT_COVERAGE
        gap_date = points[500].date
        assert all(point.date > gap_date for series in result.series for point in series.points)
    else:
        assert result.status == SignalStatus.UNAVAILABLE
        assert result.availability.reason_code == SignalAvailabilityReason.INSUFFICIENT_INPUT_COVERAGE
    assert result.availability.input_coverage.internal_gap_count == 1


@pytest.mark.asyncio
async def test_all_plugins_preserve_same_internal_date_gap_without_compaction(
    neutral_points,
):
    points = neutral_points["volatile"][-1000:]
    points = [point for index, point in enumerate(points) if index != 500]
    results = await SignalService().compute(
        default_requests(),
        points,
        SignalExecutionContext(
            domain=SignalDomain.ASSET,
            requested_range=DateRangeModel(
                start=points[0].date,
                end=points[-1].date,
            ),
            source_reference="asset:matrix-gap",
        ),
    )

    by_code = {result.signal_code: result for result in results}
    assert all(by_code[code].status == SignalStatus.PARTIAL for code in PARTIAL_CONTIGUOUS_CODES)
    assert all(by_code[code].status == SignalStatus.UNAVAILABLE for code in EXPECTED_CODES - PARTIAL_CONTIGUOUS_CODES)
    assert all(result.availability.input_coverage.internal_gap_count == 1 for result in results)


@pytest.mark.asyncio
async def test_irregular_range_outside_loaded_data_is_unavailable(
    neutral_points,
):
    points = neutral_points["volatile"][-1000:]
    requested_start = points[-1].date + timedelta(days=10)
    context = SignalExecutionContext(
        domain=SignalDomain.ASSET,
        requested_range=DateRangeModel(
            start=requested_start,
            end=requested_start + timedelta(days=10),
        ),
        cadence=SignalCadence.IRREGULAR,
        source_reference="asset:irregular-outside",
    )
    results = await SignalService().compute(
        default_requests(),
        points,
        context,
    )

    assert all(result.status == SignalStatus.UNAVAILABLE for result in results)
    assert all(result.error is None for result in results)


@pytest.mark.asyncio
async def test_invalid_instance_does_not_erase_valid_matrix(
    neutral_points,
):
    points = neutral_points["volatile"]
    requests = [
        SignalRequest(
            instance_id="invalid-ema",
            signal_code="EMA",
            params={"period": 1},
        ),
        *default_requests(),
    ]
    results = await SignalService().compute(
        requests,
        points,
        execution_context(points),
    )

    assert results[0].status == SignalStatus.FAILED
    assert results[0].error.code == SignalErrorCode.INVALID_PARAMS
    assert all(result.status == SignalStatus.OK for result in results[1:])


def test_all_warmup_contracts_are_internally_consistent(
    neutral_points,
):
    points = neutral_points["volatile"]
    context = execution_context(points)
    for code in EXPECTED_CODES:
        plugin_class = SignalPluginRegistry.get_plugin(code)
        requirement = plugin_class.warmup_requirement(
            plugin_class.validate_params({}),
            context,
        )
        assert requirement.total_points == requirement.minimum_points + requirement.stabilization_points
        assert requirement.normalized_tolerance == 1e-6
