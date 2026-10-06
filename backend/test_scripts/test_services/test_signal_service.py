"""Tests for library-agnostic SignalService orchestration."""

from __future__ import annotations

import inspect
import math
import sys
from datetime import date, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.app.schemas.common import BackwardFillInfo, DateRangeModel
from backend.app.schemas.prices import AssetBackwardFillInfo
from backend.app.schemas.signals import (
    SignalAvailabilityReason,
    SignalBandComponent,
    SignalBandPoint,
    SignalBandValueSource,
    SignalCadence,
    SignalComputation,
    SignalDataPolicy,
    SignalDomain,
    SignalErrorCode,
    SignalExecutionContext,
    SignalInputRequirements,
    SignalLineCrossoverRequest,
    SignalLineSeries,
    SignalOutputValueSource,
    SignalPriceField,
    SignalPricePoint,
    SignalPriceValueSource,
    SignalRequest,
    SignalSourceCapability,
    SignalStatus,
    SignalThresholdCrossingRequest,
    SignalValuePoint,
    SignalVolumeKind,
    SignalWarningCode,
)
from backend.app.services import signal_service as signal_service_module
from backend.app.services.provider_registry import SignalPluginRegistry
from backend.app.services.signal_plugins.base import SignalUnavailableError
from backend.app.services.signal_service import (
    SignalRequestValidationError,
    SignalService,
)
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


class SparseInputLinePlugin(PartialLinePlugin):
    signal_code = "TEST_SPARSE_INPUT_LINE"
    allows_sparse_input_dates = True


class CalendarPartialLinePlugin(PartialLinePlugin):
    """``PartialLinePlugin`` computed on its calendar input: the reference for the partial-coverage warning."""

    signal_code = "TEST_CALENDAR_PARTIAL_LINE"
    computes_on_quote_days = False


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


class WrongVisualMetadataPlugin(LineFixturePlugin):
    signal_code = "TEST_WRONG_VISUAL_METADATA"

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
        output["series"][0]["style"]["color_role"] = "secondary"
        return output


class WrongSemanticMetadataPlugin(LineFixturePlugin):
    signal_code = "TEST_WRONG_SEMANTIC_METADATA"

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
        output["series"][0]["semantic_id"] = "unexpected.semantic"
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


class SparseSubsetDatesPlugin(LineFixturePlugin):
    signal_code = "TEST_SPARSE_SUBSET_DATES"
    allows_sparse_output_dates = True
    output_indexes = (0, 2, 4)

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
        points = output["series"][0]["points"]
        output["series"][0]["points"] = [points[index] for index in self.output_indexes]
        return output


class SparseDuplicateDatesPlugin(SparseSubsetDatesPlugin):
    signal_code = "TEST_SPARSE_DUPLICATE_DATES"
    output_indexes = (0, 0, 2)


class SparseUnsortedDatesPlugin(SparseSubsetDatesPlugin):
    signal_code = "TEST_SPARSE_UNSORTED_DATES"
    output_indexes = (2, 0)


class SparseForeignDatePlugin(SparseSubsetDatesPlugin):
    signal_code = "TEST_SPARSE_FOREIGN_DATE"

    def compute(self, price_points, event_points, params, context):
        output = super().compute(
            price_points,
            event_points,
            params,
            context,
        )
        output["series"][0]["points"][-1]["date"] = price_points[-1].date + timedelta(days=1)
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
                    semantic_id=spec.semantic_id,
                    semantic_description=spec.semantic_description,
                    unit=spec.unit,
                    axis=spec.axis,
                    points=points,
                )
            ]
        )


class AnyEventOnlyPlugin(EventOnlyPlugin):
    signal_code = "TEST_ANY_EVENT_ONLY"
    input_requirements = SignalInputRequirements(requires_events=True)


class HookRecordingPlugin(LineFixturePlugin):
    """Records validate_input/validate_output invocations for hook-wiring tests."""

    signal_code = "TEST_HOOK_RECORDING"
    validate_input_calls: list[tuple] = []
    validate_output_calls: list[tuple] = []

    @classmethod
    def validate_input(cls, price_points, event_points, params, context):
        cls.validate_input_calls.append((tuple(price_points), tuple(event_points), params, context))

    @classmethod
    def validate_output(cls, computation, price_points, event_points, params, context):
        cls.validate_output_calls.append((computation, tuple(price_points), tuple(event_points), params, context))


class RejectingValidateInputPlugin(LineFixturePlugin):
    """validate_input always rejects — used to test isolation of input-hook failures."""

    signal_code = "TEST_REJECT_VALIDATE_INPUT"

    @classmethod
    def validate_input(cls, price_points, event_points, params, context):
        raise SignalUnavailableError(
            "fixture rejects all input",
            reason_code=SignalAvailabilityReason.MISSING_SOURCE_CAPABILITY,
        )


class RejectingValidateOutputPlugin(LineFixturePlugin):
    """validate_output always rejects — used to test isolation of output-hook failures."""

    signal_code = "TEST_REJECT_VALIDATE_OUTPUT"

    @classmethod
    def validate_output(cls, computation, price_points, event_points, params, context):
        raise ValueError("fixture rejects all output")


@pytest.fixture(autouse=True)
def reset_fixture_registry():
    FixtureSignalPluginRegistry._plugins = {}
    FixtureSignalPluginRegistry._discovery_done = False
    FixtureSignalPluginRegistry._discovery_errors = ()
    HookRecordingPlugin.validate_input_calls = []
    HookRecordingPlugin.validate_output_calls = []
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

    assert len(plan.computations) == 3
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
    assert result.availability.input_coverage.max_consecutive_missing_points == 1


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
    assert warning.details["max_consecutive_missing_points"] == 1


@pytest.mark.asyncio
async def test_partial_policy_warning_describes_the_calendar_segment_not_its_quote_days():
    """The partial-coverage warning describes the calendar segment the coverage chose.

    Computing on quote days is a separate contract: the plugin receives only the segment's sessions, while the
    warning keeps the segment's calendar bounds and excludes only the input points outside it — the carried
    days inside the segment are not excluded. The same plugin computing on its calendar input says the same.
    """
    service = make_service(PartialLinePlugin, CalendarPartialLinePlugin)
    hole = date(2026, 1, 16)  # a Friday with no point at all: the weekend after it carries Thursday's bar
    sessions = [point for point in weekday_sessions(date(2026, 1, 5), 15) if point.date != hole]
    points = [point for point in calendar_filled(sessions, date(2026, 1, 25)) if point.date != hole]
    carried = [point.date for point in points if point.backward_fill_info is not None and point.backward_fill_info.days_back > 0]
    # Premise: carried weekends before the hole, right after it, and at the end of the input.
    assert carried == [date(2026, 1, 10), date(2026, 1, 11), date(2026, 1, 17), date(2026, 1, 18), date(2026, 1, 24), date(2026, 1, 25)]

    results = await service.compute(
        [
            request("quote-days", "TEST_PARTIAL_LINE", {"length": 2}),
            request("calendar", "TEST_CALENDAR_PARTIAL_LINE", {"length": 2}),
        ],
        points,
        make_context(start=date(2026, 1, 5), end=date(2026, 1, 25)),
    )
    results_by_id = {result.instance_id: result for result in results}
    on_quote_days = results_by_id["quote-days"]
    on_calendar = results_by_id["calendar"]

    assert (PartialLinePlugin.computes_on_quote_days, CalendarPartialLinePlugin.computes_on_quote_days) == (True, False)
    for result in (on_quote_days, on_calendar):
        assert (result.status, result.availability.reason_code, result.availability.partial_coverage_used) == (SignalStatus.PARTIAL, SignalAvailabilityReason.DATA_GAP, True), result.instance_id
    # A dense plugin is dated on exactly the points it received, and the requested range covers the whole input.
    # Premise: the calendar twin received the segment the coverage chose, Saturday 17 to Sunday 25, and it holds carried days.
    segment = [point.date for point in on_calendar.series[0].points]
    assert segment == [date(2026, 1, 17) + timedelta(days=offset) for offset in range(9)]
    assert [day for day in segment if day in carried] == [date(2026, 1, 17), date(2026, 1, 18), date(2026, 1, 24), date(2026, 1, 25)]
    # Premise: the quote-day plugin received only the segment's sessions, Monday 19 to Friday 23 — fewer points than the segment.
    received = [point.date for point in on_quote_days.series[0].points]
    assert received == [date(2026, 1, 19) + timedelta(days=offset) for offset in range(5)]
    assert len(received) < len(segment)

    details = {}
    for result in (on_quote_days, on_calendar):
        warning = next(item for item in result.warnings if item.code == SignalWarningCode.DATA_GAP)
        details[result.instance_id] = {key: warning.details[key] for key in ("selected_start_date", "selected_end_date", "excluded_points", "first_excluded_date")}
    # The eleven points before the hole are excluded, their carried weekend included; the carried days inside the
    # segment are not, and the bounds are the segment's own calendar days.
    assert details["calendar"] == {
        "selected_start_date": "2026-01-17",
        "selected_end_date": "2026-01-25",
        "excluded_points": 11,
        "first_excluded_date": "2026-01-05",
    }
    assert details["quote-days"] == details["calendar"]


@pytest.mark.asyncio
async def test_sparse_input_opt_in_keeps_all_valid_dates_without_compacting_sibling():
    service = make_service(
        PartialLinePlugin,
        SparseInputLinePlugin,
    )
    points = without_dates(2)

    results = await service.compute(
        [
            request(
                "contiguous",
                "TEST_PARTIAL_LINE",
                {"length": 2},
            ),
            request(
                "sparse",
                "TEST_SPARSE_INPUT_LINE",
                {"length": 2},
            ),
        ],
        points,
        make_context(start=date(2026, 1, 1)),
    )
    results_by_id = {result.instance_id: result for result in results}
    contiguous = results_by_id["contiguous"]
    sparse = results_by_id["sparse"]

    assert PartialLinePlugin.allows_sparse_input_dates is False
    assert SparseInputLinePlugin.allows_sparse_input_dates is True
    assert contiguous.status == SignalStatus.PARTIAL
    assert sparse.status == SignalStatus.PARTIAL
    assert contiguous.availability.reason_code == SignalAvailabilityReason.DATA_GAP
    assert sparse.availability.reason_code == SignalAvailabilityReason.DATA_GAP
    assert [point.date for point in contiguous.series[0].points] == [
        date(2026, 1, 4),
        date(2026, 1, 5),
        date(2026, 1, 6),
    ]
    assert [point.date for point in sparse.series[0].points] == [
        date(2026, 1, 1),
        date(2026, 1, 2),
        date(2026, 1, 4),
        date(2026, 1, 5),
        date(2026, 1, 6),
    ]


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
    assert coverage.max_consecutive_missing_points == 1


@pytest.mark.asyncio
async def test_coverage_tracks_longest_consecutive_missing_run():
    service = make_service(HighPartialPlugin)
    points = make_signal_price_points()
    points[-2:] = [point.model_copy(update={"high": None}) for point in points[-2:]]
    result = (
        await service.compute(
            [request("high", "TEST_HIGH_PARTIAL", {"length": 2})],
            points,
            make_context(start=date(2026, 1, 1)),
        )
    )[0]

    coverage = result.availability.input_coverage
    assert coverage.missing_points == 2
    assert coverage.max_consecutive_missing_points == 2


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
async def test_validate_input_and_validate_output_hooks_are_invoked_with_selected_data():
    service = make_service(HookRecordingPlugin)
    context = make_context()
    price_points = make_signal_price_points()
    result = (
        await service.compute(
            [request("hooked", "TEST_HOOK_RECORDING", {"length": 2})],
            price_points,
            context,
        )
    )[0]

    assert result.status == SignalStatus.OK
    assert len(HookRecordingPlugin.validate_input_calls) == 1
    assert len(HookRecordingPlugin.validate_output_calls) == 1

    input_price_points, input_event_points, input_params, input_context = HookRecordingPlugin.validate_input_calls[0]
    assert len(input_price_points) > 0
    assert input_event_points == ()
    assert input_params.length == 2
    assert input_context.source_capability == context.source_capability

    output_computation, output_price_points, output_event_points, output_params, output_context = HookRecordingPlugin.validate_output_calls[0]
    assert output_computation.series[0].key == "average"
    assert output_price_points == input_price_points
    assert output_params.length == 2
    assert output_context.source_capability == context.source_capability


@pytest.mark.asyncio
async def test_validate_input_rejection_is_isolated_from_valid_signal():
    service = make_service(RejectingValidateInputPlugin)
    results = await service.compute(
        [
            request("rejected", "TEST_REJECT_VALIDATE_INPUT"),
            request("valid", "FIXTURE_LINE", {"length": 2}),
        ],
        make_signal_price_points(),
        make_context(),
    )

    assert results[0].status == SignalStatus.UNAVAILABLE
    assert results[0].availability.reason_code == SignalAvailabilityReason.MISSING_SOURCE_CAPABILITY
    assert results[1].status == SignalStatus.OK


@pytest.mark.asyncio
async def test_validate_output_rejection_is_isolated_from_valid_signal():
    service = make_service(RejectingValidateOutputPlugin)
    results = await service.compute(
        [
            request("rejected", "TEST_REJECT_VALIDATE_OUTPUT"),
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
        (WrongVisualMetadataPlugin, "TEST_WRONG_VISUAL_METADATA"),
        (
            WrongSemanticMetadataPlugin,
            "TEST_WRONG_SEMANTIC_METADATA",
        ),
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
async def test_dense_default_rejects_output_missing_selected_date():
    service = make_service(WrongDatesPlugin)
    result = (
        await service.compute(
            [request("dense-missing", "TEST_WRONG_DATES", {"length": 2})],
            make_signal_price_points(),
            make_context(),
        )
    )[0]

    assert WrongDatesPlugin.allows_sparse_output_dates is False
    assert result.status == SignalStatus.FAILED
    assert result.error.code == SignalErrorCode.CONTRACT_VIOLATION


@pytest.mark.asyncio
async def test_sparse_output_accepts_sorted_unique_selected_date_subset():
    service = make_service(SparseSubsetDatesPlugin)
    result = (
        await service.compute(
            [
                request(
                    "sparse-subset",
                    "TEST_SPARSE_SUBSET_DATES",
                    {"length": 2},
                )
            ],
            make_signal_price_points(),
            make_context(),
        )
    )[0]

    assert result.status == SignalStatus.OK
    assert result.error is None
    assert [point.date for point in result.series[0].points] == [
        date(2026, 1, 3),
        date(2026, 1, 5),
    ]


@pytest.mark.asyncio
async def test_sparse_output_rejects_duplicate_dates():
    service = make_service(SparseDuplicateDatesPlugin)
    result = (
        await service.compute(
            [
                request(
                    "sparse-duplicate",
                    "TEST_SPARSE_DUPLICATE_DATES",
                    {"length": 2},
                )
            ],
            make_signal_price_points(),
            make_context(),
        )
    )[0]

    assert result.status == SignalStatus.FAILED
    # Series-level date uniqueness is validated before the service can compare
    # the sparse subset with its selected input dates.
    assert result.error.code == SignalErrorCode.INVALID_OUTPUT


@pytest.mark.asyncio
async def test_sparse_output_rejects_unsorted_dates():
    service = make_service(SparseUnsortedDatesPlugin)
    result = (
        await service.compute(
            [
                request(
                    "sparse-unsorted",
                    "TEST_SPARSE_UNSORTED_DATES",
                    {"length": 2},
                )
            ],
            make_signal_price_points(),
            make_context(),
        )
    )[0]

    assert result.status == SignalStatus.FAILED
    # Series-level ordering is validated before the cross-input date contract.
    assert result.error.code == SignalErrorCode.INVALID_OUTPUT


@pytest.mark.asyncio
async def test_sparse_output_rejects_foreign_date():
    service = make_service(SparseForeignDatePlugin)
    result = (
        await service.compute(
            [
                request(
                    "sparse-foreign",
                    "TEST_SPARSE_FOREIGN_DATE",
                    {"length": 2},
                )
            ],
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
    with pytest.raises(SignalRequestValidationError, match="annotation source"):
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


def test_annotation_plan_validates_band_source_contracts():
    service = make_service()
    requests = [
        request("band", "FIXTURE_BAND_COMPOSITE"),
        request("line", "FIXTURE_LINE", {"length": 2}),
    ]
    valid = SignalThresholdCrossingRequest(
        key="band-lower-threshold",
        attach_to_instance_id="band",
        source=SignalBandValueSource(
            instance_id="band",
            series_key="envelope",
            component=SignalBandComponent.LOWER,
        ),
        threshold=100,
    )

    plan = service.prepare_plan(requests, make_context(), [valid])
    assert plan.annotation_requests == (valid,)

    with pytest.raises(SignalRequestValidationError, match="is not a band"):
        service.prepare_plan(
            requests,
            make_context(),
            [
                valid.model_copy(
                    update={
                        "source": SignalBandValueSource(
                            instance_id="line",
                            series_key="average",
                            component=SignalBandComponent.MIDDLE,
                        )
                    }
                )
            ],
        )
    with pytest.raises(SignalRequestValidationError, match="is not declared"):
        service.prepare_plan(
            requests,
            make_context(),
            [
                valid.model_copy(
                    update={
                        "source": SignalBandValueSource(
                            instance_id="band",
                            series_key="missing",
                            component=SignalBandComponent.UPPER,
                        )
                    }
                )
            ],
        )
    with pytest.raises(SignalRequestValidationError, match="is a band"):
        service.prepare_plan(
            requests,
            make_context(),
            [
                valid.model_copy(
                    update={
                        "source": SignalOutputValueSource(
                            instance_id="band",
                            series_key="envelope",
                        )
                    }
                )
            ],
        )

    scalar_missing_series = valid.model_copy(
        update={
            "source": SignalOutputValueSource(
                instance_id="line",
                series_key="missing",
            )
        }
    )
    scalar_plan = service.prepare_plan(
        requests,
        make_context(),
        [scalar_missing_series],
    )
    assert scalar_plan.annotation_requests == (scalar_missing_series,)

    invalid_component = valid.model_dump(mode="json")
    invalid_component["source"]["component"] = "median"
    with pytest.raises(ValidationError, match="component"):
        service.prepare_plan(
            requests,
            make_context(),
            [invalid_component],
        )


@pytest.mark.asyncio
async def test_bollinger_and_donchian_band_crossings_are_plugin_agnostic():
    points = make_signal_price_points()
    annotations = [
        SignalLineCrossoverRequest(
            key="price-bollinger-upper",
            attach_to_instance_id="bollinger",
            left=SignalPriceValueSource(field=SignalPriceField.CLOSE),
            right=SignalBandValueSource(
                instance_id="bollinger",
                series_key="bands",
                component=SignalBandComponent.UPPER,
            ),
        ),
        SignalLineCrossoverRequest(
            key="price-donchian-middle",
            attach_to_instance_id="donchian",
            left=SignalPriceValueSource(field=SignalPriceField.CLOSE),
            right=SignalBandValueSource(
                instance_id="donchian",
                series_key="channels",
                component=SignalBandComponent.MIDDLE,
            ),
        ),
    ]
    results = await SignalService(SignalPluginRegistry).compute(
        [
            request(
                "bollinger",
                "BOLLINGER",
                {"period": 2, "multiplier": 0.5},
            ),
            request("donchian", "DONCHIAN", {"period": 2}),
        ],
        points,
        make_context(),
        annotation_requests=annotations,
    )

    assert [result.status for result in results] == [
        SignalStatus.OK,
        SignalStatus.OK,
    ]
    assert {annotation.key for annotation in results[0].annotations} == {"price-bollinger-upper"}
    assert {annotation.key for annotation in results[1].annotations} == {"price-donchian-middle"}
    assert all(warning.code != SignalWarningCode.ANNOTATION_UNAVAILABLE for result in results for warning in result.warnings)


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


# =============================================================================
# Quote days (developer's decision of 30/09/2026)
#
# «Sui giorni di quotazione, come la definizione standard: SMA 200 = 200 sedute.»
# A quote day is a point with ``backward_fill_info is None``. A plugin that
# computes on quote days (``SignalPlugin.computes_on_quote_days``, True by
# default) receives only the quote days of its selected points: its warm-up,
# minimum and visible units count those sessions, and its output is dated on
# them. The input coverage keeps its calendar meaning.
#
# The calendar-filled input below is exactly what the Asset adapter serves for
# a five-day market: one point per calendar day, each weekend day a copy of
# Friday's bar with ``backward_fill_info`` naming Friday.
# =============================================================================

QUOTE_DAY_FIRST_MONDAY = date(2024, 1, 1)
QUOTE_DAY_SESSIONS = 400
QUOTE_DAY_SIGNAL_CODES = ("SMA", "EMA", "RSI", "MACD", "BOLLINGER", "ATR", "OBV")
QUOTE_DAY_CAPABILITY = SignalSourceCapability(
    supports_meaningful_volume=True,
    volume_kind=SignalVolumeKind.TRADED_SHARES,
)


def session_bar(day: date, index: int) -> SignalPricePoint:
    """A deterministic OHLCV bar whose close never repeats the previous session's."""
    cycle = index % 23 - 11
    wobble = (index * 5) % 7 - 3
    close = Decimal(10_000 + 3 * index + 40 * cycle + 25 * wobble) / Decimal(100)
    open_ = close - Decimal(index % 5 - 2) / Decimal(10)
    return SignalPricePoint(
        date=day,
        open=open_,
        high=max(open_, close) + Decimal(1 + index % 3) / Decimal(10),
        low=min(open_, close) - Decimal(1 + index % 4) / Decimal(10),
        close=close,
        volume=Decimal(1_000_000 + (index * 7_919) % 50_000),
    )


def weekday_sessions(first_monday: date, sessions: int) -> list[SignalPricePoint]:
    """One genuine quote per weekday, and nothing on weekends."""
    points: list[SignalPricePoint] = []
    day = first_monday
    while len(points) < sessions:
        if day.weekday() < 5:
            points.append(session_bar(day, len(points)))
        day += timedelta(days=1)
    return points


def calendar_filled(sessions: list[SignalPricePoint], end: date) -> list[SignalPricePoint]:
    """The same quotes with every missing calendar day carried from the last one, through ``end``."""
    quotes = {point.date: point for point in sessions}
    filled: list[SignalPricePoint] = []
    last = sessions[0]
    day = sessions[0].date
    while day <= end:
        quote = quotes.get(day)
        if quote is not None:
            last = quote
            filled.append(quote)
        else:
            filled.append(
                last.model_copy(
                    update={
                        "date": day,
                        "backward_fill_info": BackwardFillInfo(
                            actual_rate_date=last.date,
                            days_back=(day - last.date).days,
                        ),
                    }
                )
            )
        day += timedelta(days=1)
    return filled


def two_filled_weeks() -> list[SignalPricePoint]:
    """Monday 2026-01-05 to Sunday 2026-01-18: ten quotes, four carried weekend days."""
    return calendar_filled(weekday_sessions(date(2026, 1, 5), 10), date(2026, 1, 18))


def quote_day_context(start: date, end: date) -> SignalExecutionContext:
    return SignalExecutionContext(
        domain=SignalDomain.ASSET,
        requested_range=DateRangeModel(start=start, end=end),
        cadence=SignalCadence.DAILY,
        source_reference="asset:quote-days",
        source_capability=QUOTE_DAY_CAPABILITY,
    )


def point_values(point) -> tuple[float | None, ...]:
    if isinstance(point, SignalBandPoint):
        return (point.lower, point.middle, point.upper)
    return (point.value,)


def same_values(left, right) -> bool:
    return all((actual is None and expected is None) or (actual is not None and expected is not None and math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-9)) for actual, expected in zip(point_values(left), point_values(right), strict=True))


@pytest.mark.asyncio
@pytest.mark.parametrize("signal_code", QUOTE_DAY_SIGNAL_CODES)
async def test_session_plugin_on_a_calendar_filled_input_equals_the_plugin_on_its_quote_days(signal_code):
    """T1 — the property: carrying Friday onto the weekend changes nothing an indicator computes."""
    sessions = weekday_sessions(QUOTE_DAY_FIRST_MONDAY, QUOTE_DAY_SESSIONS)
    visible_end = sessions[-1].date + timedelta(days=2)  # the Sunday after the last quote
    visible_start = visible_end - timedelta(days=57)  # a Saturday: the range opens on a day with no quote
    filled = calendar_filled(sessions, visible_end)
    context = quote_day_context(visible_start, visible_end)
    visible_quote_days = [point.date for point in sessions if visible_start <= point.date <= visible_end]
    # Premise: weekdays quoted, every weekend day carried, and warm-up to spare in sessions.
    assert [point.date for point in filled if point.backward_fill_info is None] == [point.date for point in sessions]
    assert len(filled) == (visible_end - sessions[0].date).days + 1
    assert visible_start.weekday() == 5
    assert len(visible_quote_days) == 40

    result = (
        await SignalService(SignalPluginRegistry).compute(
            [request(signal_code.lower(), signal_code)],
            filled,
            context,
        )
    )[0]

    plugin_class = SignalPluginRegistry.get_plugin(signal_code)
    reference = SignalService._normalize_computation(
        plugin_class().compute(
            sessions,
            [],
            plugin_class.validate_params({}),
            context,
        )
    )
    assert result.status == SignalStatus.OK, result.availability
    assert [series.key for series in result.series] == [series.key for series in reference.series]
    assert [point.date for series in result.series for point in series.points if point.date.weekday() >= 5] == [], f"{signal_code} is dated on weekend days that have no quote"
    for series, expected in zip(result.series, reference.series, strict=True):
        expected_points = [point for point in expected.points if visible_start <= point.date <= visible_end]
        assert [point.date for point in series.points] == visible_quote_days, f"{signal_code}.{series.key} is not dated on the visible quote days"
        assert [point.date for point in expected_points] == visible_quote_days
        mismatched = [point.date.isoformat() for point, reference_point in zip(series.points, expected_points, strict=True) if not same_values(point, reference_point)]
        assert mismatched == [], f"{signal_code}.{series.key} differs from the plugin computed on its quote days"


@pytest.mark.asyncio
async def test_calendar_rolling_return_keeps_computing_on_the_calendar_input():
    """T2 — guard: calendar windows are calendar days by design, carried weekends included."""
    sessions = weekday_sessions(QUOTE_DAY_FIRST_MONDAY, 60)
    visible_end = sessions[-1].date + timedelta(days=2)  # a Sunday
    visible_start = visible_end - timedelta(days=20)  # a Monday, three weeks
    filled = calendar_filled(sessions, visible_end)
    by_date = {point.date: point for point in filled}

    result = (
        await SignalService(SignalPluginRegistry).compute(
            [request("calendar", "ASSET_CALENDAR_ROLLING_RETURN", {"window_days": 7})],
            filled,
            quote_day_context(visible_start, visible_end),
        )
    )[0]

    assert result.status == SignalStatus.OK
    series = result.series[0]
    assert [point.date for point in series.points] == [visible_start + timedelta(days=offset) for offset in range(21)]
    for point in series.points:
        current = by_date[point.date]
        reference = by_date[point.date - timedelta(days=7)]
        assert point.value == pytest.approx((float(current.close) / float(reference.close) - 1) * 100)
    saturday = next(point for point in series.points if point.date.weekday() == 5)
    friday = saturday.date - timedelta(days=1)
    assert saturday.provenance.current_price_date == friday
    assert saturday.provenance.current_price_days_back == 1
    assert saturday.provenance.reference_target_date == saturday.date - timedelta(days=7)
    assert saturday.provenance.reference_price_date == friday - timedelta(days=7)
    assert saturday.provenance.reference_price_days_back == 1
    # Its warm-up counts calendar points, carried ones included.
    assert result.warmup.used_points == (visible_start - filled[0].date).days


@pytest.mark.asyncio
async def test_warmup_counts_quote_days_not_calendar_points():
    """T3 — five sessions satisfy a five-session warm-up and not a six-session one, although
    seven calendar points precede the range."""
    service = make_service()
    filled = two_filled_weeks()
    visible_start = date(2026, 1, 12)
    before = [point for point in filled if point.date < visible_start]
    assert (len(before), sum(point.backward_fill_info is None for point in before)) == (7, 5)

    exact, short = await service.compute(
        [
            request("exact", "FIXTURE_WARMUP", {"minimum_points": 2, "stabilization_points": 3}),
            request("short", "FIXTURE_WARMUP", {"minimum_points": 2, "stabilization_points": 4}),
        ],
        filled,
        make_context(start=visible_start, end=date(2026, 1, 18)),
    )

    assert exact.status == SignalStatus.OK
    assert (exact.warmup.used_points, exact.warmup.complete) == (5, True)
    assert short.status == SignalStatus.PARTIAL
    assert short.availability.reason_code == SignalAvailabilityReason.INCOMPLETE_WARMUP
    assert (short.warmup.used_points, short.warmup.complete) == (5, False)
    warning = next(item for item in short.warnings if item.code == SignalWarningCode.INCOMPLETE_WARMUP)
    assert (warning.details["used_points"], warning.details["required_points"]) == (5, 6)


@pytest.mark.asyncio
async def test_minimum_history_counts_quote_days():
    """T3 — seven calendar points but five sessions cannot feed a six-point minimum."""
    service = make_service()
    week = calendar_filled(weekday_sessions(date(2026, 1, 5), 5), date(2026, 1, 11))
    assert len(week) == 7

    result = (
        await service.compute(
            [request("six", "FIXTURE_WARMUP", {"minimum_points": 6, "stabilization_points": 0})],
            week,
            make_context(start=date(2026, 1, 5), end=date(2026, 1, 11)),
        )
    )[0]

    assert result.status == SignalStatus.UNAVAILABLE
    assert result.availability.reason_code == SignalAvailabilityReason.INSUFFICIENT_HISTORY
    assert result.series == []


@pytest.mark.asyncio
async def test_a_visible_range_without_quote_days_is_unavailable():
    """T3 — visible units count sessions: a weekend of carried days has none."""
    service = make_service()
    week = calendar_filled(weekday_sessions(date(2026, 1, 5), 5), date(2026, 1, 11))

    result = (
        await service.compute(
            [request("line", "FIXTURE_LINE", {"length": 2})],
            week,
            make_context(start=date(2026, 1, 10), end=date(2026, 1, 11)),
        )
    )[0]

    assert result.status == SignalStatus.UNAVAILABLE
    assert result.availability.reason_code == SignalAvailabilityReason.INSUFFICIENT_HISTORY
    assert result.series == []
    coverage = result.availability.input_coverage
    assert (coverage.available_points, coverage.observed_points, coverage.backfilled_points) == (7, 5, 2)


def quoted_with_carried_rate(point: SignalPricePoint, *, rate_days_back: int) -> SignalPricePoint:
    """A genuine quote converted with an exchange rate carried from ``rate_days_back`` days earlier."""
    return point.model_copy(
        update={
            "backward_fill_info": AssetBackwardFillInfo(
                actual_rate_date=point.date,
                days_back=0,
                fx_rate_date=point.date - timedelta(days=rate_days_back),
                fx_days_back=rate_days_back,
            )
        }
    )


def carried_price(last_quote: SignalPricePoint, day: date) -> SignalPricePoint:
    """No quote on ``day``: the last quote's price carried onto it, converted with that day's own rate."""
    return last_quote.model_copy(
        update={
            "date": day,
            "backward_fill_info": AssetBackwardFillInfo(
                actual_rate_date=last_quote.date,
                days_back=(day - last_quote.date).days,
                fx_rate_date=day,
                fx_days_back=0,
            ),
        }
    )


@pytest.mark.asyncio
async def test_a_quote_converted_with_a_carried_rate_is_a_session_and_a_carried_price_is_not():
    """Decision 1 (30/09/2026): the price decides a session, not the exchange rate.

    A genuine quote converted with a rate carried from an earlier day (``days_back == 0``,
    ``fx_days_back > 0``) reaches the plugin and counts as warm-up. A price carried from an
    earlier day (``days_back > 0``) does neither, even converted with a fresh rate.
    """
    service = make_service(HookRecordingPlugin)
    points = two_filled_weeks()
    assert [points[index].date for index in (1, 3, 9, 10)] == [date(2026, 1, 6), date(2026, 1, 8), date(2026, 1, 14), date(2026, 1, 15)]
    points[1] = quoted_with_carried_rate(points[1], rate_days_back=1)  # Tuesday, in the warm-up
    points[3] = carried_price(points[2], points[3].date)  # Thursday, in the warm-up
    points[9] = quoted_with_carried_rate(points[9], rate_days_back=2)  # Wednesday, visible
    points[10] = carried_price(points[9], points[10].date)  # Thursday, visible
    # Premise: every one of those four carries a backfill record; only the price tells them apart.
    assert [(points[index].backward_fill_info.days_back, points[index].backward_fill_info.fx_days_back) for index in (1, 3, 9, 10)] == [(0, 1), (1, 0), (0, 2), (1, 0)]

    result = (
        await service.compute(
            [request("line", "TEST_HOOK_RECORDING", {"length": 4})],
            points,
            make_context(start=date(2026, 1, 12), end=date(2026, 1, 18)),
        )
    )[0]

    ((reached, _events, _params, _context),) = HookRecordingPlugin.validate_input_calls
    assert [point.date for point in reached] == [
        date(2026, 1, 5),
        date(2026, 1, 6),  # quoted, converted with a carried rate: a session
        date(2026, 1, 7),
        date(2026, 1, 9),
        date(2026, 1, 12),
        date(2026, 1, 13),
        date(2026, 1, 14),  # quoted, converted with a carried rate: a session
        date(2026, 1, 16),
    ]
    # Four warm-up sessions for a four-session warm-up: Monday, Tuesday, Wednesday and Friday.
    assert (result.warmup.used_points, result.warmup.complete) == (4, True)
    assert result.status == SignalStatus.OK
    assert [point.date for point in result.series[0].points] == [date(2026, 1, 12), date(2026, 1, 13), date(2026, 1, 14), date(2026, 1, 16)]


@pytest.mark.asyncio
async def test_coverage_of_a_calendar_filled_input_keeps_its_calendar_meaning():
    """T4 — guard: coverage is the same calendar coverage as before the change, field by field."""
    service = make_service()

    result = (
        await service.compute(
            [request("line", "FIXTURE_LINE", {"length": 2})],
            two_filled_weeks(),
            make_context(start=date(2026, 1, 12), end=date(2026, 1, 18)),
        )
    )[0]

    assert result.status == SignalStatus.OK
    assert result.availability.input_coverage.model_dump(mode="python") == {
        "requested_points": 14,
        "available_points": 14,
        "contiguous_points": 14,
        "observed_points": 10,
        "backfilled_points": 4,
        "missing_points": 0,
        "max_consecutive_missing_points": 0,
        "internal_gap_count": 0,
        "coverage_ratio": 1.0,
        "field_coverage": {SignalPriceField.CLOSE: 1.0},
        "event_type_counts": {},
        "first_available_date": date(2026, 1, 5),
        "last_available_date": date(2026, 1, 18),
    }


@pytest.mark.asyncio
async def test_partial_plugin_coverage_counts_calendar_slots_and_carried_days():
    """T4 — guard: a leading gap and an invalid weekday are counted on the calendar, as before."""
    service = make_service(HighPartialPlugin)
    filled = two_filled_weeks()
    assert filled[9].date == date(2026, 1, 14)
    filled[9] = filled[9].model_copy(update={"high": None})

    result = (
        await service.compute(
            [request("high", "TEST_HIGH_PARTIAL", {"length": 2})],
            filled,
            make_context(start=date(2026, 1, 2), end=date(2026, 1, 18)),
        )
    )[0]

    assert result.availability.input_coverage.model_dump(mode="python") == {
        "requested_points": 17,
        "available_points": 13,
        "contiguous_points": 9,
        "observed_points": 9,
        "backfilled_points": 4,
        "missing_points": 4,
        "max_consecutive_missing_points": 3,
        "internal_gap_count": 1,
        "coverage_ratio": 13 / 17,
        "field_coverage": {SignalPriceField.CLOSE: 14 / 17, SignalPriceField.HIGH: 13 / 17},
        "event_type_counts": {},
        "first_available_date": date(2026, 1, 5),
        "last_available_date": date(2026, 1, 18),
    }
