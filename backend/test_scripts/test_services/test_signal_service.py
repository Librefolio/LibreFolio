"""Tests for library-agnostic SignalService orchestration."""

from __future__ import annotations

import inspect
import sys
from datetime import date, timedelta

import pytest

from backend.app.schemas.common import BackwardFillInfo, DateRangeModel
from backend.app.schemas.signals import (
    SignalAvailabilityReason,
    SignalComputation,
    SignalDataPolicy,
    SignalDomain,
    SignalErrorCode,
    SignalExecutionContext,
    SignalInputRequirements,
    SignalLineSeries,
    SignalOutputValueSource,
    SignalPriceField,
    SignalPriceValueSource,
    SignalRequest,
    SignalStatus,
    SignalThresholdCrossingRequest,
    SignalValuePoint,
    SignalWarningCode,
)
from backend.app.services import signal_service as signal_service_module
from backend.app.services.signal_service import SignalService
from backend.test_scripts.fixtures.signal_plugins.events_fixture import (
    EventsFixturePlugin,
)
from backend.test_scripts.fixtures.signal_plugins.line_fixture import (
    LineFixturePlugin,
)
from backend.test_scripts.fixtures.signal_plugins.registry import (
    FixtureSignalPluginRegistry,
)
from backend.test_scripts.fixtures.signals import (
    make_signal_price_points,
)

FIXTURE_NAMESPACE = "backend.test_scripts.fixtures.signal_plugins"


class PartialLinePlugin(LineFixturePlugin):
    signal_code = "TEST_PARTIAL_LINE"
    input_requirements = SignalInputRequirements(
        price_fields=[SignalPriceField.CLOSE],
        data_policy=SignalDataPolicy.ALLOW_PARTIAL_CONTIGUOUS,
        minimum_coverage=0.5,
    )


class HighStrictPlugin(LineFixturePlugin):
    signal_code = "TEST_HIGH_STRICT"
    input_requirements = SignalInputRequirements(
        price_fields=[SignalPriceField.CLOSE, SignalPriceField.HIGH],
    )


class HighPartialPlugin(LineFixturePlugin):
    signal_code = "TEST_HIGH_PARTIAL"
    input_requirements = SignalInputRequirements(
        price_fields=[SignalPriceField.CLOSE, SignalPriceField.HIGH],
        data_policy=SignalDataPolicy.ALLOW_PARTIAL_CONTIGUOUS,
        minimum_coverage=0.5,
    )


class PlanningFailurePlugin(LineFixturePlugin):
    signal_code = "TEST_PLANNING_FAILURE"

    @classmethod
    def warmup_requirement(cls, params, context):
        raise RuntimeError("fixture planning failure")


class NanOutputPlugin(LineFixturePlugin):
    signal_code = "TEST_NAN_OUTPUT"

    def compute(self, price_points, event_points, params, context):
        output = (
            super()
            .compute(
                price_points,
                event_points,
                params,
                context,
            )
            .model_dump(mode="python")
        )
        output["series"][0]["points"][0]["value"] = float("nan")
        return output


class InfinityOutputPlugin(LineFixturePlugin):
    signal_code = "TEST_INFINITY_OUTPUT"

    def compute(self, price_points, event_points, params, context):
        output = (
            super()
            .compute(
                price_points,
                event_points,
                params,
                context,
            )
            .model_dump(mode="python")
        )
        output["series"][0]["points"][0]["value"] = float("inf")
        return output


class WrongMetadataPlugin(LineFixturePlugin):
    signal_code = "TEST_WRONG_METADATA"

    def compute(self, price_points, event_points, params, context):
        output = (
            super()
            .compute(
                price_points,
                event_points,
                params,
                context,
            )
            .model_dump(mode="python")
        )
        output["series"][0]["key"] = "unexpected"
        return output


class WrongDatesPlugin(LineFixturePlugin):
    signal_code = "TEST_WRONG_DATES"

    def compute(self, price_points, event_points, params, context):
        output = (
            super()
            .compute(
                price_points,
                event_points,
                params,
                context,
            )
            .model_dump(mode="python")
        )
        output["series"][0]["points"] = output["series"][0]["points"][1:]
        return output


class EventOnlyPlugin(EventsFixturePlugin):
    signal_code = "TEST_EVENT_ONLY"
    input_requirements = SignalInputRequirements(
        requires_events=True,
        event_types=["DIVIDEND"],
    )

    def compute(self, price_points, event_points, params, context):
        cumulative = 0.0
        points: list[SignalValuePoint] = []
        spec = self.output_specs[0]
        for event in event_points:
            cumulative += float(event.value or 0)
            points.append(
                SignalValuePoint(
                    date=event.date,
                    value=cumulative,
                )
            )
        return SignalComputation(
            series=[
                SignalLineSeries(
                    key=spec.key,
                    label_key=spec.label_key,
                    unit=spec.unit,
                    axis=spec.axis,
                    points=points,
                )
            ]
        )


class AnyEventOnlyPlugin(EventOnlyPlugin):
    signal_code = "TEST_ANY_EVENT_ONLY"
    input_requirements = SignalInputRequirements(requires_events=True)


@pytest.fixture(autouse=True)
def reset_fixture_registry():
    FixtureSignalPluginRegistry._plugins = {}
    FixtureSignalPluginRegistry._discovery_done = False
    FixtureSignalPluginRegistry._discovery_errors = ()
    for module_name in tuple(sys.modules):
        if module_name.startswith(f"{FIXTURE_NAMESPACE}.") and module_name != f"{FIXTURE_NAMESPACE}.registry":
            sys.modules.pop(module_name, None)
    yield


def make_context(
    *,
    start: date = date(2026, 1, 3),
    end: date = date(2026, 1, 6),
    domain: SignalDomain = SignalDomain.ASSET,
) -> SignalExecutionContext:
    return SignalExecutionContext(
        domain=domain,
        requested_range=DateRangeModel(start=start, end=end),
        source_reference=f"{domain.value}:fixture",
    )


def make_service(*plugins: type) -> SignalService:
    FixtureSignalPluginRegistry.auto_discover()
    for plugin in plugins:
        FixtureSignalPluginRegistry.register(plugin)
    return SignalService(FixtureSignalPluginRegistry)


def request(
    instance_id: str,
    signal_code: str,
    params: dict | None = None,
) -> SignalRequest:
    return SignalRequest(
        instance_id=instance_id,
        signal_code=signal_code,
        params=params or {},
    )


def without_dates(*indexes: int):
    excluded = set(indexes)
    return [point for index, point in enumerate(make_signal_price_points()) if index not in excluded]


@pytest.mark.asyncio
async def test_bulk_plan_deduplicates_and_aggregates_requirements():
    service = make_service()
    requests = [
        request("line-a", "FIXTURE_LINE", {"length": 3}),
        request("line-b", "FIXTURE_LINE", {"length": 3}),
        request(
            "warmup",
            "FIXTURE_WARMUP",
            {"minimum_points": 3, "stabilization_points": 7},
        ),
        request("events", "FIXTURE_EVENTS"),
    ]

    plan = service.prepare_plan(requests, make_context())

    assert plan.unique_computation_count == 3
    assert plan.max_total_points == 10
    assert plan.max_history_points_before_visible == 10
    assert plan.required_price_fields == frozenset({SignalPriceField.CLOSE})
    assert plan.requires_events is True
    assert plan.required_event_types == frozenset({"DIVIDEND"})
    line_plan = next(item for item in plan.computations if item.plugin_class.signal_code == "FIXTURE_LINE")
    assert line_plan.instance_ids == ("line-a", "line-b")


def test_duplicate_instance_ids_are_rejected():
    service = make_service()
    with pytest.raises(ValueError, match="instance_id"):
        service.prepare_plan(
            [
                request("duplicate", "FIXTURE_LINE"),
                request("duplicate", "FIXTURE_WARMUP"),
            ],
            make_context(),
        )


@pytest.mark.asyncio
async def test_unknown_and_invalid_params_are_isolated_preflight_failures():
    service = make_service()
    plan = service.prepare_plan(
        [
            request("unknown", "DOES_NOT_EXIST"),
            request("invalid", "FIXTURE_LINE", {"length": 1}),
            request("valid", "FIXTURE_LINE", {"length": 2}),
        ],
        make_context(),
    )

    results = await service.execute(plan, make_signal_price_points())

    assert [result.instance_id for result in results] == [
        "unknown",
        "invalid",
        "valid",
    ]
    assert results[0].error.code == SignalErrorCode.UNKNOWN_SIGNAL
    assert results[0].availability is None
    assert results[1].error.code == SignalErrorCode.INVALID_PARAMS
    assert results[1].error.details["validation_errors"]
    assert results[2].status == SignalStatus.OK


@pytest.mark.asyncio
async def test_planning_failure_does_not_block_other_signals():
    service = make_service(PlanningFailurePlugin)
    plan = service.prepare_plan(
        [
            request("broken", "TEST_PLANNING_FAILURE"),
            request("valid", "FIXTURE_LINE", {"length": 2}),
        ],
        make_context(),
    )

    results = await service.execute(plan, make_signal_price_points())

    assert results[0].status == SignalStatus.FAILED
    assert results[0].error.code == SignalErrorCode.PLANNING_ERROR
    assert results[0].availability is None
    assert results[1].status == SignalStatus.OK


@pytest.mark.asyncio
async def test_deduplicated_signal_computes_once_and_fans_out(monkeypatch):
    service = make_service()
    plugin_class = FixtureSignalPluginRegistry.get_plugin("FIXTURE_LINE")
    original_compute = plugin_class.compute
    calls = 0

    def counted_compute(self, *args, **kwargs):
        nonlocal calls
        calls += 1
        return original_compute(self, *args, **kwargs)

    monkeypatch.setattr(plugin_class, "compute", counted_compute)
    plan = service.prepare_plan(
        [
            request("first", "FIXTURE_LINE", {"length": 2}),
            request("second", "FIXTURE_LINE", {"length": 2}),
        ],
        make_context(),
    )

    results = await service.execute(plan, make_signal_price_points())

    assert calls == 1
    assert [result.instance_id for result in results] == ["first", "second"]
    assert results[0].series == results[1].series


@pytest.mark.asyncio
async def test_complete_history_returns_ok_and_slices_visible_range():
    service = make_service()
    result = (
        await service.compute(
            [request("line", "FIXTURE_LINE", {"length": 2})],
            make_signal_price_points(),
            make_context(),
        )
    )[0]

    assert result.status == SignalStatus.OK
    assert [point.date for point in result.series[0].points] == [
        date(2026, 1, 3),
        date(2026, 1, 4),
        date(2026, 1, 5),
        date(2026, 1, 6),
    ]
    assert all(point.value is not None for point in result.series[0].points)


@pytest.mark.asyncio
async def test_incomplete_warmup_returns_partial_with_warning():
    service = make_service()
    result = (
        await service.compute(
            [
                request(
                    "warmup",
                    "FIXTURE_WARMUP",
                    {"minimum_points": 2, "stabilization_points": 8},
                )
            ],
            make_signal_price_points(),
            make_context(),
        )
    )[0]

    assert result.status == SignalStatus.PARTIAL
    assert result.availability.reason_code == SignalAvailabilityReason.INCOMPLETE_WARMUP
    assert result.warmup.complete is False
    assert result.warnings[0].code == SignalWarningCode.INCOMPLETE_WARMUP


@pytest.mark.asyncio
async def test_no_finite_visible_output_is_unavailable_not_failed():
    service = make_service()
    result = (
        await service.compute(
            [request("line", "FIXTURE_LINE", {"length": 5})],
            make_signal_price_points(),
            make_context(
                start=date(2026, 1, 1),
                end=date(2026, 1, 3),
            ),
        )
    )[0]

    assert result.status == SignalStatus.UNAVAILABLE
    assert result.availability.reason_code == SignalAvailabilityReason.INSUFFICIENT_HISTORY
    assert result.error is None


@pytest.mark.asyncio
async def test_visible_ramp_up_with_some_values_is_partial_not_failed():
    service = make_service()
    result = (
        await service.compute(
            [request("line", "FIXTURE_LINE", {"length": 5})],
            make_signal_price_points(),
            make_context(),
        )
    )[0]

    assert result.status == SignalStatus.PARTIAL
    assert result.availability.reason_code == SignalAvailabilityReason.INCOMPLETE_WARMUP
    assert [point.value for point in result.series[0].points] == [
        None,
        None,
        102.4,
        104.0,
    ]


@pytest.mark.asyncio
async def test_insufficient_minimum_history_is_unavailable():
    service = make_service()
    points = make_signal_price_points()[:3]
    result = (
        await service.compute(
            [request("line", "FIXTURE_LINE", {"length": 5})],
            points,
            make_context(start=date(2026, 1, 1), end=date(2026, 1, 3)),
        )
    )[0]

    assert result.status == SignalStatus.UNAVAILABLE
    assert result.availability.reason_code == SignalAvailabilityReason.INSUFFICIENT_HISTORY
    assert result.series == []


@pytest.mark.asyncio
async def test_missing_required_field_is_recalculated_at_execution():
    service = make_service(HighStrictPlugin)
    plan = service.prepare_plan(
        [request("high", "TEST_HIGH_STRICT", {"length": 2})],
        make_context(),
    )
    points = [point.model_copy(update={"high": None}) for point in make_signal_price_points()]

    result = (await service.execute(plan, points))[0]

    assert result.status == SignalStatus.UNAVAILABLE
    assert result.availability.reason_code == SignalAvailabilityReason.MISSING_INPUT_FIELDS
    assert result.availability.missing_price_fields == [SignalPriceField.HIGH]


@pytest.mark.asyncio
async def test_strict_internal_gap_is_unavailable_without_compaction():
    service = make_service()
    points = without_dates(2)
    result = (
        await service.compute(
            [request("line", "FIXTURE_LINE", {"length": 2})],
            points,
            make_context(start=date(2026, 1, 1)),
        )
    )[0]

    assert result.status == SignalStatus.UNAVAILABLE
    assert result.availability.reason_code == SignalAvailabilityReason.INSUFFICIENT_INPUT_COVERAGE
    assert result.availability.input_coverage.internal_gap_count == 1
    assert result.availability.input_coverage.requested_points == 6


@pytest.mark.asyncio
async def test_partial_policy_uses_contiguous_suffix_and_warns():
    service = make_service(PartialLinePlugin)
    result = (
        await service.compute(
            [request("line", "TEST_PARTIAL_LINE", {"length": 2})],
            without_dates(2),
            make_context(start=date(2026, 1, 1)),
        )
    )[0]

    assert result.status == SignalStatus.PARTIAL
    assert result.availability.reason_code == SignalAvailabilityReason.DATA_GAP
    assert result.availability.partial_coverage_used is True
    assert [point.date for point in result.series[0].points] == [
        date(2026, 1, 4),
        date(2026, 1, 5),
        date(2026, 1, 6),
    ]
    assert any(warning.code == SignalWarningCode.DATA_GAP for warning in result.warnings)
    warning = next(warning for warning in result.warnings if warning.code == SignalWarningCode.DATA_GAP)
    assert warning.details["selected_start_date"] == "2026-01-04"
    assert warning.details["selected_end_date"] == "2026-01-06"
    assert warning.details["excluded_points"] == 2


@pytest.mark.asyncio
async def test_partial_policy_falls_back_to_longest_sufficient_segment():
    service = make_service(PartialLinePlugin)
    result = (
        await service.compute(
            [request("line", "TEST_PARTIAL_LINE", {"length": 2})],
            without_dates(4),
            make_context(start=date(2026, 1, 1)),
        )
    )[0]

    assert result.status == SignalStatus.PARTIAL
    assert result.availability.reason_code == SignalAvailabilityReason.DATA_GAP
    assert [point.date for point in result.series[0].points] == [
        date(2026, 1, 1),
        date(2026, 1, 2),
        date(2026, 1, 3),
        date(2026, 1, 4),
    ]


@pytest.mark.asyncio
async def test_partial_policy_is_unavailable_when_no_segment_meets_minimum():
    service = make_service(PartialLinePlugin)
    result = (
        await service.compute(
            [request("line", "TEST_PARTIAL_LINE", {"length": 2})],
            without_dates(1, 3, 5),
            make_context(start=date(2026, 1, 1)),
        )
    )[0]

    assert result.status == SignalStatus.UNAVAILABLE
    assert result.availability.reason_code == SignalAvailabilityReason.INSUFFICIENT_HISTORY


@pytest.mark.asyncio
async def test_partial_policy_breaks_longest_run_ties_with_most_recent_segment():
    service = make_service(PartialLinePlugin)
    base = make_signal_price_points()
    points = [
        *base,
        base[-1].model_copy(
            update={
                "date": base[-1].date + timedelta(days=1),
            }
        ),
    ]
    points = [point for index, point in enumerate(points) if index not in {2, 5}]
    result = (
        await service.compute(
            [request("line", "TEST_PARTIAL_LINE", {"length": 2})],
            points,
            make_context(start=date(2026, 1, 1)),
        )
    )[0]

    assert result.status == SignalStatus.PARTIAL
    assert [point.date for point in result.series[0].points] == [
        date(2026, 1, 4),
        date(2026, 1, 5),
    ]


@pytest.mark.asyncio
async def test_partial_field_coverage_uses_suffix_without_compaction():
    service = make_service(HighPartialPlugin)
    points = make_signal_price_points()
    points[2] = points[2].model_copy(update={"high": None})
    result = (
        await service.compute(
            [request("high", "TEST_HIGH_PARTIAL", {"length": 2})],
            points,
            make_context(start=date(2026, 1, 1)),
        )
    )[0]

    assert result.status == SignalStatus.PARTIAL
    assert result.availability.reason_code == SignalAvailabilityReason.PARTIAL_INPUT_COVERAGE
    assert [point.date for point in result.series[0].points] == [
        date(2026, 1, 4),
        date(2026, 1, 5),
        date(2026, 1, 6),
    ]


@pytest.mark.asyncio
async def test_missing_visible_boundaries_are_counted_in_coverage():
    service = make_service()
    points = make_signal_price_points()[1:5]
    result = (
        await service.compute(
            [request("line", "FIXTURE_LINE", {"length": 2})],
            points,
            make_context(start=date(2026, 1, 1)),
        )
    )[0]

    coverage = result.availability.input_coverage
    assert result.status == SignalStatus.UNAVAILABLE
    assert coverage.requested_points == 6
    assert coverage.available_points == 4
    assert coverage.missing_points == 2


@pytest.mark.asyncio
async def test_coverage_tracks_observed_and_backfilled_points():
    service = make_service()
    points = make_signal_price_points()
    points[1] = points[1].model_copy(
        update={
            "backward_fill_info": BackwardFillInfo(
                actual_rate_date=date(2026, 1, 1),
                days_back=1,
            )
        }
    )
    result = (
        await service.compute(
            [request("line", "FIXTURE_LINE", {"length": 2})],
            points,
            make_context(),
        )
    )[0]

    coverage = result.availability.input_coverage
    assert coverage.observed_points == 5
    assert coverage.backfilled_points == 1


@pytest.mark.asyncio
async def test_event_loading_is_explicit_and_empty_loaded_events_are_valid():
    service = make_service()
    plan = service.prepare_plan(
        [request("events", "FIXTURE_EVENTS")],
        make_context(),
    )

    not_loaded = (
        await service.execute(
            plan,
            make_signal_price_points(),
            [],
            events_loaded=False,
        )
    )[0]
    loaded_empty = (
        await service.execute(
            plan,
            make_signal_price_points(),
            [],
            events_loaded=True,
        )
    )[0]

    assert plan.requires_events is True
    assert not_loaded.status == SignalStatus.UNAVAILABLE
    assert not_loaded.availability.reason_code == SignalAvailabilityReason.MISSING_EVENT_TYPES
    assert loaded_empty.status == SignalStatus.OK
    assert all(point.value == 0 for point in loaded_empty.series[0].points)


@pytest.mark.asyncio
async def test_event_only_plugin_uses_previsible_events_as_warmup():
    from backend.test_scripts.fixtures.signals import make_signal_event_points  # noqa: PLC0415

    service = make_service(EventOnlyPlugin)
    plan = service.prepare_plan(
        [request("events", "TEST_EVENT_ONLY")],
        make_context(
            start=date(2026, 1, 5),
            end=date(2026, 1, 5),
        ),
    )

    result = (
        await service.execute(
            plan,
            [],
            make_signal_event_points(),
            events_loaded=True,
        )
    )[0]

    assert result.status == SignalStatus.OK
    assert result.warmup.loaded_points == 2
    assert result.warmup.used_points == 1
    assert result.series[0].points[0].date == date(2026, 1, 5)
    assert result.series[0].points[0].value == 3.5


@pytest.mark.asyncio
async def test_event_only_plugin_without_visible_events_is_unavailable():
    from backend.test_scripts.fixtures.signals import make_signal_event_points  # noqa: PLC0415

    service = make_service(EventOnlyPlugin)
    result = (
        await service.compute(
            [request("events", "TEST_EVENT_ONLY")],
            [],
            make_context(
                start=date(2026, 1, 10),
                end=date(2026, 1, 10),
            ),
            event_points=make_signal_event_points(),
            events_loaded=True,
        )
    )[0]

    assert result.status == SignalStatus.UNAVAILABLE
    assert result.availability.reason_code == SignalAvailabilityReason.INSUFFICIENT_HISTORY


@pytest.mark.asyncio
async def test_requires_any_event_reports_not_loaded_with_wildcard():
    service = make_service(AnyEventOnlyPlugin)
    result = (
        await service.compute(
            [request("events", "TEST_ANY_EVENT_ONLY")],
            [],
            make_context(),
            events_loaded=False,
        )
    )[0]

    assert result.status == SignalStatus.UNAVAILABLE
    assert result.availability.reason_code == SignalAvailabilityReason.MISSING_EVENT_TYPES
    assert result.availability.missing_event_types == ["*"]


@pytest.mark.asyncio
async def test_compute_failure_is_isolated_from_valid_signal():
    service = make_service()
    results = await service.compute(
        [
            request("broken", "FIXTURE_FAILING"),
            request("valid", "FIXTURE_LINE", {"length": 2}),
        ],
        make_signal_price_points(),
        make_context(),
    )

    assert results[0].status == SignalStatus.FAILED
    assert results[0].error.code == SignalErrorCode.COMPUTE_ERROR
    assert results[1].status == SignalStatus.OK


@pytest.mark.asyncio
async def test_unexpected_orchestration_failure_is_isolated(monkeypatch):
    service = make_service()
    original_execute = service._execute_planned_signal

    def conditional_failure(planned, *args):
        if planned.plugin_class.signal_code == "FIXTURE_WARMUP":
            raise RuntimeError("orchestration fixture failure")
        return original_execute(planned, *args)

    monkeypatch.setattr(
        service,
        "_execute_planned_signal",
        conditional_failure,
    )
    results = await service.compute(
        [
            request("broken", "FIXTURE_WARMUP"),
            request("valid", "FIXTURE_LINE", {"length": 2}),
        ],
        make_signal_price_points(),
        make_context(),
    )

    assert results[0].status == SignalStatus.FAILED
    assert results[0].error.code == SignalErrorCode.PLANNING_ERROR
    assert results[0].error.details["phase"] == "orchestration"
    assert results[1].status == SignalStatus.OK


@pytest.mark.asyncio
async def test_nan_is_sanitized_before_visible_slicing():
    service = make_service(NanOutputPlugin)
    result = (
        await service.compute(
            [request("nan", "TEST_NAN_OUTPUT", {"length": 2})],
            make_signal_price_points(),
            make_context(start=date(2026, 1, 3)),
        )
    )[0]

    assert result.status == SignalStatus.OK
    assert all(point.value is not None for point in result.series[0].points)


@pytest.mark.asyncio
async def test_infinity_is_failed_as_invalid_output():
    service = make_service(InfinityOutputPlugin)
    result = (
        await service.compute(
            [request("infinity", "TEST_INFINITY_OUTPUT", {"length": 2})],
            make_signal_price_points(),
            make_context(),
        )
    )[0]

    assert result.status == SignalStatus.FAILED
    assert result.error.code == SignalErrorCode.INVALID_OUTPUT
    assert "infinity" in result.error.message


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("plugin", "code"),
    [
        (WrongMetadataPlugin, "TEST_WRONG_METADATA"),
        (WrongDatesPlugin, "TEST_WRONG_DATES"),
    ],
)
async def test_output_contract_violations_are_failed(plugin, code):
    service = make_service(plugin)
    result = (
        await service.compute(
            [request("invalid", code, {"length": 2})],
            make_signal_price_points(),
            make_context(),
        )
    )[0]

    assert result.status == SignalStatus.FAILED
    assert result.error.code == SignalErrorCode.CONTRACT_VIOLATION


@pytest.mark.asyncio
async def test_equivalent_asset_and_fx_neutral_points_match():
    service = make_service()
    requests = [request("line", "FIXTURE_LINE", {"length": 2})]
    price_points = make_signal_price_points()

    asset_result = (
        await service.compute(
            requests,
            price_points,
            make_context(domain=SignalDomain.ASSET),
        )
    )[0]
    fx_result = (
        await service.compute(
            requests,
            price_points,
            make_context(domain=SignalDomain.FX),
        )
    )[0]

    assert asset_result.series == fx_result.series
    assert asset_result.normalized_params == fx_result.normalized_params


@pytest.mark.asyncio
async def test_execute_uses_one_to_thread_call_for_entire_batch(monkeypatch):
    service = make_service()
    calls = 0

    async def tracked_to_thread(function, *args):
        nonlocal calls
        calls += 1
        return function(*args)

    monkeypatch.setattr(
        signal_service_module.asyncio,
        "to_thread",
        tracked_to_thread,
    )
    plan = service.prepare_plan(
        [
            request("line", "FIXTURE_LINE", {"length": 2}),
            request(
                "warmup",
                "FIXTURE_WARMUP",
                {"minimum_points": 2, "stabilization_points": 0},
            ),
        ],
        make_context(),
    )

    results = await service.execute(plan, make_signal_price_points())

    assert calls == 1
    assert [result.status for result in results] == [
        SignalStatus.OK,
        SignalStatus.OK,
    ]


def test_annotation_plan_validates_refs_and_adds_price_requirements():
    service = make_service()
    requests = [request("line", "FIXTURE_LINE", {"length": 2})]
    annotation = {
        "kind": "threshold_crossing",
        "key": "high-threshold",
        "attach_to_instance_id": "line",
        "source": {
            "kind": "price",
            "field": "high",
        },
        "threshold": 103,
    }

    plan = service.prepare_plan(
        requests,
        make_context(),
        [annotation],
    )

    assert len(plan.annotation_requests) == 1
    assert plan.required_price_fields == frozenset(
        {
            SignalPriceField.CLOSE,
            SignalPriceField.HIGH,
        }
    )
    with pytest.raises(ValueError, match="keys must be unique"):
        service.prepare_plan(
            requests,
            make_context(),
            [annotation, annotation],
        )
    with pytest.raises(ValueError, match="annotation target"):
        service.prepare_plan(
            requests,
            make_context(),
            [
                {
                    **annotation,
                    "attach_to_instance_id": "missing",
                }
            ],
        )
    with pytest.raises(ValueError, match="annotation source"):
        service.prepare_plan(
            requests,
            make_context(),
            [
                {
                    **annotation,
                    "source": {
                        "kind": "signal",
                        "instance_id": "missing",
                        "series_key": "average",
                    },
                }
            ],
        )


@pytest.mark.asyncio
async def test_annotation_uses_extended_output_before_visible_slicing():
    service = make_service()
    annotation = SignalThresholdCrossingRequest(
        key="average-threshold",
        attach_to_instance_id="line",
        source=SignalOutputValueSource(
            instance_id="line",
            series_key="average",
        ),
        threshold=102,
    )

    result = (
        await service.compute(
            [request("line", "FIXTURE_LINE", {"length": 2})],
            make_signal_price_points(),
            make_context(start=date(2026, 1, 4)),
            annotation_requests=[annotation],
        )
    )[0]

    assert result.status == SignalStatus.OK
    assert [point.date for point in result.series[0].points] == [
        date(2026, 1, 4),
        date(2026, 1, 5),
        date(2026, 1, 6),
    ]
    assert len(result.annotations) == 1
    assert result.annotations[0].date == date(2026, 1, 4)


@pytest.mark.asyncio
async def test_unavailable_annotation_source_adds_target_warning():
    service = make_service()
    annotation = SignalThresholdCrossingRequest(
        key="unknown-source",
        attach_to_instance_id="line",
        source=SignalOutputValueSource(
            instance_id="unknown",
            series_key="average",
        ),
        threshold=0,
    )

    results = await service.compute(
        [
            request("unknown", "DOES_NOT_EXIST"),
            request("line", "FIXTURE_LINE", {"length": 2}),
        ],
        make_signal_price_points(),
        make_context(),
        annotation_requests=[annotation],
    )

    assert results[0].status == SignalStatus.FAILED
    assert results[1].status == SignalStatus.OK
    assert results[1].annotations == []
    assert any(warning.code == SignalWarningCode.ANNOTATION_UNAVAILABLE for warning in results[1].warnings)


@pytest.mark.asyncio
async def test_computed_annotation_is_not_attached_to_failed_target():
    service = make_service()
    annotation = SignalThresholdCrossingRequest(
        key="failed-target",
        attach_to_instance_id="broken",
        source=SignalOutputValueSource(
            instance_id="line",
            series_key="average",
        ),
        threshold=102,
    )

    results = await service.compute(
        [
            request("line", "FIXTURE_LINE", {"length": 2}),
            request("broken", "FIXTURE_FAILING"),
        ],
        make_signal_price_points(),
        make_context(start=date(2026, 1, 4)),
        annotation_requests=[annotation],
    )

    assert results[1].status == SignalStatus.FAILED
    assert results[1].annotations == []
    assert any(warning.code == SignalWarningCode.ANNOTATION_UNAVAILABLE for warning in results[1].warnings)


@pytest.mark.asyncio
async def test_annotation_batch_failure_warns_for_every_request(monkeypatch):
    service = make_service()

    def fail_annotations(*args, **kwargs):
        raise RuntimeError("annotation batch fixture failure")

    monkeypatch.setattr(
        service.annotation_service,
        "compute",
        fail_annotations,
    )
    annotations = [
        SignalThresholdCrossingRequest(
            key="first-annotation",
            attach_to_instance_id="line",
            source=SignalPriceValueSource(),
            threshold=101,
        ),
        SignalThresholdCrossingRequest(
            key="second-annotation",
            attach_to_instance_id="line",
            source=SignalPriceValueSource(),
            threshold=103,
        ),
    ]

    result = (
        await service.compute(
            [request("line", "FIXTURE_LINE", {"length": 2})],
            make_signal_price_points(),
            make_context(),
            annotation_requests=annotations,
        )
    )[0]

    annotation_warnings = [warning for warning in result.warnings if warning.code == SignalWarningCode.ANNOTATION_UNAVAILABLE]
    assert len(annotation_warnings) == 2


def test_service_has_no_indicator_library_or_domain_io_dependencies():
    source = inspect.getsource(signal_service_module)
    for forbidden in (
        "pandas_ta_classic",
        "import talib",
        "from talib",
        "AsyncSession",
        "httpx",
    ):
        assert forbidden not in source
