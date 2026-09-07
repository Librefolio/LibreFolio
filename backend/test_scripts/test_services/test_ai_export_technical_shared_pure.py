"""Pure-helper tests for the shared technical AI Export toolbox.

`components/technical_shared.py` mixes async DB builders with a layer of pure
helper functions. This file covers **only the pure layer** - weighting, series
coercion, sampling, plugin-declared bounds and the event-selection policy -
which is deliberately why the unit stays PURE (no DB, no server, no network).
The async builders around them are already exercised end-to-end by
`test_ai_export_components_technical.py`.

The helpers here are small but load-bearing: they decide which observations are
real, which rows survive sampling, and which events are shown to the model. A
silent mistake in any of them does not raise - it produces a smaller, plausible
and wrong picture of the portfolio, which is the failure mode AI Export cares
about most.

Isolation: PURE.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from backend.app.schemas.portfolio import AssetPeriodContribution
from backend.app.schemas.prices import AssetBackwardFillInfo, FAPricePoint, FAPriceQueryResult
from backend.app.schemas.signals import SignalError, SignalResult, SignalStatus
from backend.app.services.ai_export.components import technical_shared as tsh
from backend.app.services.ai_export.components.registry import ComponentRegistry
from backend.app.services.ai_export.components.technical_payloads import IndicatorBucketRow, TechnicalSingleValueCell
from backend.app.services.ai_export.components.types import DetailLevel
from backend.app.services.ai_export.dependencies import BuildContext
from backend.app.services.ai_export.temporal.aggregators import DatedValue
from backend.app.services.ai_export.temporal.points import DiscreteEvent, ObservedPoint

DAY_1 = date(2026, 2, 2)
DAY_2 = date(2026, 2, 3)
DAY_3 = date(2026, 2, 4)
AS_OF = date(2026, 3, 31)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _position(asset_id: int, end_value: Decimal | None) -> AssetPeriodContribution:
    return AssetPeriodContribution(
        asset_id=asset_id,
        asset_name=f"Asset {asset_id}",
        asset_type="stock",
        broker_id=1,
        broker_name="Broker One",
        end_value=end_value,
    )


def _price_point(day: date, close: str, *, currency: str | None = "EUR", days_back: int | None = None) -> FAPricePoint:
    backward_fill_info = None
    if days_back is not None:
        backward_fill_info = AssetBackwardFillInfo(actual_rate_date=day - timedelta(days=days_back), days_back=days_back)
    return FAPricePoint(date=day, close=Decimal(close), currency=currency, backward_fill_info=backward_fill_info)


def _price_result(*points: FAPricePoint) -> FAPriceQueryResult:
    return FAPriceQueryResult(asset_id=7, prices=list(points))


def _row(start: date, end: date) -> IndicatorBucketRow:
    return IndicatorBucketRow(
        start_date=start,
        end_date=end,
        calendar_days=(end - start).days + 1,
        observation_count=1,
        cells={"rsi": TechnicalSingleValueCell(value=50.0, date=start)},
    )


def _event(day: date, *, entity_id: str = "asset:7", key: str = "rsi_overbought", direction: str = "up", dedup: object | None = None) -> DiscreteEvent:
    return DiscreteEvent(
        date=day,
        dedup_key=dedup if dedup is not None else (entity_id, key, day.isoformat(), direction),
        payload={"entity_id": entity_id, "key": key, "direction": direction},
    )


# ---------------------------------------------------------------------------
# 1. compute_nav_weights - gross weighting so shorts still weigh in
# ---------------------------------------------------------------------------


def test_nav_weights_are_empty_for_an_empty_universe():
    assert dict(tsh.compute_nav_weights(())) == {}


def test_nav_weights_skip_positions_without_an_end_value():
    # Situation: an asset the pricing run could not value at period end. It must
    # be omitted rather than counted as zero, which would dilute every weight.
    weights = tsh.compute_nav_weights((_position(1, Decimal("100")), _position(2, None)))
    assert set(weights) == {1}
    assert weights[1] == Decimal(1)


def test_nav_weights_use_absolute_values_so_a_short_still_weighs_in():
    weights = tsh.compute_nav_weights((_position(1, Decimal("100")), _position(2, Decimal("-100"))))
    assert weights[1] == weights[2] == Decimal("0.5")


def test_nav_weights_aggregate_the_same_asset_held_at_two_brokers():
    weights = tsh.compute_nav_weights((_position(1, Decimal("60")), _position(1, Decimal("40")), _position(2, Decimal("100"))))
    assert weights[1] == weights[2] == Decimal("0.5")


def test_nav_weights_are_empty_when_gross_exposure_is_zero():
    # An all-cash (or fully closed) universe: no weight is definable, and
    # returning an empty mapping is the honest answer, not 0/0.
    assert dict(tsh.compute_nav_weights((_position(1, Decimal("0")),))) == {}


def test_nav_weights_are_returned_read_only_and_asset_sorted():
    weights = tsh.compute_nav_weights((_position(3, Decimal("50")), _position(1, Decimal("50"))))
    assert list(weights) == [1, 3]
    with pytest.raises(TypeError):
        weights[9] = Decimal(1)  # type: ignore[index]


# ---------------------------------------------------------------------------
# 2. coherent_price_currency / price_result_to_close_points
# ---------------------------------------------------------------------------


def test_coherent_currency_is_none_without_a_result():
    assert tsh.coherent_price_currency(None) is None


def test_coherent_currency_is_none_for_an_empty_series():
    assert tsh.coherent_price_currency(_price_result()) is None


def test_coherent_currency_is_none_for_a_mixed_series():
    # Situation: an asset re-denominated mid-period, or an FX conversion applied
    # to only part of the series. Charting those closes on one axis would be a
    # category error, so the series is refused rather than silently mixed.
    mixed = _price_result(_price_point(DAY_1, "10", currency="EUR"), _price_point(DAY_2, "11", currency="USD"))
    assert tsh.coherent_price_currency(mixed) is None


def test_coherent_currency_returns_the_single_series_currency():
    assert tsh.coherent_price_currency(_price_result(_price_point(DAY_1, "10"))) == "EUR"


def test_close_points_are_empty_when_the_currency_is_incoherent():
    mixed = _price_result(_price_point(DAY_1, "10", currency="EUR"), _price_point(DAY_2, "11", currency="USD"))
    assert tsh.price_result_to_close_points(mixed, start=DAY_1, end=DAY_3) == ()


def test_close_points_drop_backward_filled_carry_forwards():
    # A carry-forward is not a new observation; keeping it would flatten the
    # series and understate realized movement.
    result = _price_result(
        _price_point(DAY_1, "10"),
        _price_point(DAY_2, "10", days_back=1),
        _price_point(DAY_3, "12", days_back=0),
    )
    points = tsh.price_result_to_close_points(result, start=DAY_1, end=DAY_3)
    assert [point.date for point in points] == [DAY_1, DAY_3]


def test_close_points_are_sliced_to_the_requested_period():
    result = _price_result(_price_point(DAY_1 - timedelta(days=30), "9"), _price_point(DAY_2, "10"))
    points = tsh.price_result_to_close_points(result, start=DAY_1, end=DAY_3)
    assert [point.date for point in points] == [DAY_2]


# ---------------------------------------------------------------------------
# 3. latest_point_value / _technical_dated_value / _latest_observed_value
# ---------------------------------------------------------------------------


def test_latest_point_value_is_a_null_pair_without_points():
    assert tsh.latest_point_value((), key="close") == (None, None)


def test_latest_point_value_returns_the_last_point_for_the_requested_key():
    result = _price_result(_price_point(DAY_1, "10"), _price_point(DAY_3, "12"))
    points = tsh.price_result_to_close_points(result, start=DAY_1, end=DAY_3)
    assert tsh.latest_point_value(points, key="close") == (12.0, DAY_3)


def test_latest_point_value_reports_the_date_even_when_the_key_is_absent():
    # Situation: a multi-output series where one output is missing on the last
    # day. The date still anchors the reading; the value is honestly None.
    result = _price_result(_price_point(DAY_1, "10"))
    points = tsh.price_result_to_close_points(result, start=DAY_1, end=DAY_3)
    assert tsh.latest_point_value(points, key="signal") == (None, DAY_1)


def test_technical_dated_value_passes_none_through():
    assert tsh._technical_dated_value(None) is None


def test_technical_dated_value_converts_a_decimal_atom_to_a_float_cell():
    converted = tsh._technical_dated_value(DatedValue(value=Decimal("12.5"), observed_date=DAY_2))
    assert (converted.value, converted.date) == (12.5, DAY_2)


def test_latest_observed_value_is_none_without_points():
    assert tsh._latest_observed_value(()) is None


def test_latest_observed_value_picks_the_newest_point_regardless_of_input_order():
    # The caller may hand over an unsorted series; "latest" must mean latest by
    # date, not last in the list.
    points = (ObservedPoint(date=DAY_3, value=Decimal("3")), ObservedPoint(date=DAY_1, value=Decimal("1")))
    latest = tsh._latest_observed_value(points)
    assert (latest.value, latest.date) == (3.0, DAY_3)


# ---------------------------------------------------------------------------
# 4. _uniform_sample_rows - the sampling that keeps both endpoints
# ---------------------------------------------------------------------------


def _rows(count: int) -> tuple[IndicatorBucketRow, ...]:
    return tuple(_row(DAY_1 + timedelta(days=index), DAY_1 + timedelta(days=index)) for index in range(count))


@pytest.mark.parametrize("limit", [None, 10])
def test_sampling_returns_every_row_when_it_is_not_needed(limit: int | None):
    rows = _rows(5)
    assert tsh._uniform_sample_rows(rows, limit) == rows


def test_sampling_keeps_the_first_and_last_row():
    # The temporal endpoints are what let a reader place the series in time;
    # dropping either would silently narrow the reported window.
    rows = _rows(20)
    sampled = tsh._uniform_sample_rows(rows, 5)
    assert sampled[0] is rows[0]
    assert sampled[-1] is rows[-1]


def test_sampling_returns_a_chronological_subset_within_the_limit():
    rows = _rows(20)
    sampled = tsh._uniform_sample_rows(rows, 5)
    assert len(sampled) <= 5
    assert [row.start_date for row in sampled] == sorted(row.start_date for row in sampled)
    # Rows are pydantic models (unhashable), so identity is compared by index.
    assert all(any(row is candidate for candidate in rows) for row in sampled)


def test_sampling_spreads_evenly_rather_than_taking_a_prefix():
    rows = _rows(9)
    sampled = tsh._uniform_sample_rows(rows, 3)
    assert [rows.index(row) for row in sampled] == [0, 4, 8]


# ---------------------------------------------------------------------------
# 5. _own_param_value / _declared_zero_level - single source of truth
# ---------------------------------------------------------------------------


def test_own_param_value_reads_the_threshold_back_from_the_curated_bundle():
    # The point of this helper is that the annotation threshold and the computed
    # parameter can never drift apart, because there is only one of them.
    specs = tsh.ASSET_CURATED_SIGNALS
    rsi = next(spec for spec in specs if spec.signal_code == "RSI")
    assert tsh._own_param_value(specs, rsi.instance_id, "overbought") == float(rsi.params["overbought"])


def test_own_param_value_rejects_an_instance_absent_from_the_bundle():
    with pytest.raises(ValueError, match="no curated signal instance"):
        tsh._own_param_value(tsh.ASSET_CURATED_SIGNALS, "not_a_real_instance", "overbought")


def test_declared_zero_level_reads_the_plugins_own_reference_level():
    assert tsh._declared_zero_level("ROC", "roc") == 0.0


def test_declared_zero_level_rejects_an_unknown_plugin():
    with pytest.raises(ValueError, match="unknown curated plugin"):
        tsh._declared_zero_level("NOT_A_PLUGIN", "roc")


def test_declared_zero_level_rejects_an_output_the_plugin_does_not_declare():
    with pytest.raises(ValueError, match="declares no output"):
        tsh._declared_zero_level("ROC", "not_an_output")


def test_declared_zero_level_rejects_an_output_without_a_zero_reference():
    # Situation: the helper is pointed at an oscillator that has no natural zero
    # line, so there is nothing to anchor a crossing annotation to.
    with pytest.raises(ValueError, match="declares no 'zero' reference level"):
        tsh._declared_zero_level("RSI", "rsi")


# ---------------------------------------------------------------------------
# 6. _source_numeric_bounds - plugin-declared axis bounds, or nothing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "source",
    [
        None,
        "rsi",
        {"kind": "constant", "value": 70},
        {"kind": "signal", "instance_id": 5, "series_key": "rsi"},
        {"kind": "signal", "instance_id": "rsi_14", "series_key": None},
    ],
    ids=["absent", "not-a-mapping", "wrong-kind", "non-string-instance", "non-string-series"],
)
def test_numeric_bounds_are_absent_for_a_source_that_cannot_declare_them(source):
    # A constant threshold, or a malformed annotation source, carries no axis:
    # returning None keeps the payload honest instead of inventing a scale.
    assert tsh._source_numeric_bounds(source, {}) is None


def test_numeric_bounds_are_absent_when_the_instance_has_no_result():
    source = {"kind": "signal", "instance_id": "rsi_14", "series_key": "rsi"}
    assert tsh._source_numeric_bounds(source, {}) is None


def test_numeric_bounds_are_absent_when_the_result_names_an_unregistered_plugin():
    # Situation: a plugin is removed (or renamed) while a result carrying its old
    # signal_code is still in flight. There is no axis to read, so the annotation
    # is published without bounds instead of with invented ones.
    orphaned = SignalResult(
        instance_id="ghost_1",
        signal_code="NOT_A_REGISTERED_PLUGIN",
        status=SignalStatus.FAILED,
        error=SignalError(code="unknown_signal", message="plugin absent from the registry"),
    )
    source = {"kind": "signal", "instance_id": "ghost_1", "series_key": "rsi"}
    assert tsh._source_numeric_bounds(source, {"ghost_1": orphaned}) is None


# ---------------------------------------------------------------------------
# 7. _annotation_value_bounds - dispatch by annotation type
# ---------------------------------------------------------------------------


class _FakeAnnotation:
    """Minimal stand-in exposing only what `_annotation_value_bounds` reads."""

    def __init__(self, annotation_type: str, metadata: dict):
        self.annotation_type = annotation_type
        self.metadata = metadata


@pytest.mark.parametrize(
    "annotation_type,metadata",
    [
        ("line_crossover", {"left": {"kind": "constant"}, "right": {"kind": "constant"}}),
        ("threshold_crossing", {"source": {"kind": "constant"}}),
        ("divergence", {"source": {"kind": "constant"}}),
    ],
    ids=["crossover", "threshold", "unhandled-type"],
)
def test_annotation_bounds_are_empty_when_no_source_declares_an_axis(annotation_type: str, metadata: dict):
    # Every branch of the dispatch converges on the same honest answer when the
    # sources are constants: no bounds rather than fabricated ones.
    assert tsh._annotation_value_bounds(_FakeAnnotation(annotation_type, metadata), {}) == {}


# ---------------------------------------------------------------------------
# 8. select_technical_events - the detail-owned selection policy
# ---------------------------------------------------------------------------


def test_event_selection_is_empty_for_an_empty_input():
    selection = tsh.select_technical_events((), snapshot_as_of=AS_OF)
    assert selection.events == ()
    assert selection.summaries == ()


def test_event_selection_deduplicates_on_the_dedup_key():
    # Situation: the same annotation reaches the selector twice (e.g. an asset
    # held at two brokers). Counting it twice would overstate the detection.
    duplicated = _event(DAY_1, dedup="same-key")
    selection = tsh.select_technical_events((duplicated, _event(DAY_2, dedup="same-key")), snapshot_as_of=AS_OF)
    summary = next(item for item in selection.summaries if item.annotation_key == "rsi_overbought")
    assert summary.detected_count == 1
    assert len(selection.events) == 1


def test_event_selection_keeps_every_event_inside_the_recent_window():
    recent = tuple(_event(AS_OF - timedelta(days=index)) for index in range(3))
    selection = tsh.select_technical_events(recent, snapshot_as_of=AS_OF, detail_level=DetailLevel.FULL)
    summary = next(item for item in selection.summaries if item.annotation_key == "rsi_overbought")
    assert summary.detected_count == 3
    assert summary.recent_window_count == 3
    assert summary.exported_count == 3
    assert summary.selection_applied is False


def test_event_selection_reports_omission_when_old_events_are_dropped():
    # Old events outside the complete-recent window are trimmed to the policy
    # minimum, and `selection_applied` is what tells the reader it happened.
    old = tuple(_event(AS_OF - timedelta(days=300 + index)) for index in range(12))
    selection = tsh.select_technical_events(old, snapshot_as_of=AS_OF, detail_level=DetailLevel.STANDARD)
    summary = next(item for item in selection.summaries if item.annotation_key == "rsi_overbought")
    assert summary.detected_count == 12
    assert summary.recent_window_count == 0
    assert summary.exported_count < summary.detected_count
    assert summary.selection_applied is True
    assert len(selection.events) == summary.exported_count


def test_event_selection_exports_the_newest_events_first():
    days = [AS_OF - timedelta(days=300 + index) for index in range(6)]
    selection = tsh.select_technical_events(tuple(_event(day) for day in days), snapshot_as_of=AS_OF, detail_level=DetailLevel.STANDARD)
    exported_dates = {event.date for event in selection.events}
    assert exported_dates <= set(days)
    assert max(exported_dates) == max(days)


def test_event_selection_groups_per_entity_and_annotation_key():
    events = (_event(AS_OF, entity_id="asset:7"), _event(AS_OF, entity_id="asset:8"), _event(AS_OF, key="rsi_oversold", direction="down"))
    selection = tsh.select_technical_events(events, snapshot_as_of=AS_OF)
    groups = {(summary.entity_id, summary.annotation_key) for summary in selection.summaries}
    assert groups == {("asset:7", "rsi_overbought"), ("asset:8", "rsi_overbought"), ("asset:7", "rsi_oversold")}


def test_event_selection_counts_directions_over_the_whole_detection():
    events = (_event(AS_OF, direction="up"), _event(AS_OF - timedelta(days=1), direction="down"), _event(AS_OF - timedelta(days=2), direction="up"))
    selection = tsh.select_technical_events(events, snapshot_as_of=AS_OF)
    summary = next(item for item in selection.summaries if item.annotation_key == "rsi_overbought")
    assert (summary.upward_count, summary.downward_count) == (2, 1)


def test_event_selection_rejects_a_non_mapping_payload():
    # The selector reads `entity_id`/`key` out of the payload; a non-mapping
    # payload means the caller built a `DiscreteEvent` for a different purpose.
    with pytest.raises(TypeError, match="technical event payload must be a mapping"):
        tsh.select_technical_events((DiscreteEvent(date=AS_OF, dedup_key="k", payload="not-a-mapping"),), snapshot_as_of=AS_OF)


@pytest.mark.parametrize(
    "payload,message",
    [
        ({"key": "rsi_overbought"}, "requires entity_id"),
        ({"entity_id": "", "key": "rsi_overbought"}, "requires entity_id"),
        ({"entity_id": "asset:7"}, "requires annotation key"),
        ({"entity_id": "asset:7", "key": ""}, "requires annotation key"),
    ],
    ids=["no-entity", "empty-entity", "no-key", "empty-key"],
)
def test_event_selection_rejects_a_payload_without_its_grouping_identity(payload: dict, message: str):
    with pytest.raises(ValueError, match=message):
        tsh.select_technical_events((DiscreteEvent(date=AS_OF, dedup_key="k", payload=payload),), snapshot_as_of=AS_OF)


# ---------------------------------------------------------------------------
# 9. build_events_payload - the bucket plan is not optional
# ---------------------------------------------------------------------------


def test_build_events_payload_requires_a_bucket_plan():
    # Situation: the events payload is built from a context created for resolver
    # use only. Without a plan there is no temporal axis to assign events to, so
    # failing loudly beats emitting an empty, plausible-looking payload.
    context = BuildContext(ComponentRegistry(()), request_id="technical-shared-unit")
    with pytest.raises(ValueError, match="event payload construction requires bucket_plan"):
        tsh.build_events_payload((), context)
