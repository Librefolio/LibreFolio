"""Pure-helper tests for the shared technical AI Export toolbox.

`components/technical_shared.py` mixes async DB builders with a layer of pure
helper functions. This file covers **only the pure layer** - weighting, series
coercion, sampling, plugin-declared bounds, the event-selection policy, why a
price result gives no series (E-AI503) and the gaps of a series (E-23) -
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

import inspect
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, get_args

import pytest

from backend.app.schemas.portfolio import AssetPeriodContribution
from backend.app.schemas.prices import AssetBackwardFillInfo, FAPricePoint, FAPriceQueryResult
from backend.app.schemas.signals import SignalError, SignalResult, SignalStatus
from backend.app.services.ai_export.components import technical_payloads
from backend.app.services.ai_export.components import technical_shared as tsh
from backend.app.services.ai_export.components.registry import ComponentRegistry
from backend.app.services.ai_export.components.resources import FxRateObservation, FxRateSeriesResource
from backend.app.services.ai_export.components.technical_payloads import IndicatorBucketRow, TechnicalSingleValueCell
from backend.app.services.ai_export.components.types import DetailLevel
from backend.app.services.ai_export.dependencies import BuildContext
from backend.app.services.ai_export.temporal.aggregators import DatedValue
from backend.app.services.ai_export.temporal.plan import Bucket, BucketPlan
from backend.app.services.ai_export.temporal.points import ContinuousMultiOutputPoint, DiscreteEvent, ObservedPoint
from backend.app.services.ai_export.temporal.policy import BucketDetailLevel, BucketingPolicy

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


# ---------------------------------------------------------------------------
# 10. price_series_gap - why a held asset has no price series (E-AI503)
# ---------------------------------------------------------------------------
#
# Decided on the points the price history returns, NEVER on the asset type
# (developer's decision, 19/10/2026). `result.prices` is already sliced to the
# period, carried points included: empty means no stored price dated up to the
# period end. Read through the module (`tsh.price_series_gap`), so that today
# only these tests are red, never the file's collection.


@pytest.mark.parametrize(
    ("result", "expected"),
    [
        pytest.param(None, "no_stored_price", id="no-result"),
        pytest.param(_price_result(), "no_stored_price", id="no-point"),
        pytest.param(_price_result(_price_point(DAY_1, "10"), _price_point(DAY_2, "11")), None, id="one-currency"),
        pytest.param(_price_result(_price_point(DAY_1, "10", currency="EUR"), _price_point(DAY_2, "11", currency="USD")), "mixed_price_currencies", id="two-currencies"),
        pytest.param(_price_result(_price_point(DAY_1, "10", currency=None)), "mixed_price_currencies", id="points-without-a-currency"),
    ],
)
def test_price_series_gap_names_why_a_result_has_no_coherent_series(result: FAPriceQueryResult | None, expected: str | None):
    """AI503-S01 — red until E-AI503: the reason a price result gives no series, read from its points alone.

    No result or no point: ``no_stored_price``. Points sharing one currency, at least one of them observed, give no
    gap. Points that do not share one (two currencies, or none at all, which ``price_history.currency NOT NULL`` makes
    impossible) give ``mixed_price_currencies``. For these two codes the builders write ``coherent_price_currency`` as
    the currency, so a code is named exactly when that is None.

    A series of carried points only (a stale series) gave no gap here until E-23, which names it ``no_price_in_period``
    and keeps its currency: that case moved to E23-S16.
    """
    gap = tsh.price_series_gap(result)

    assert gap == expected
    assert (gap is None) == (tsh.coherent_price_currency(result) is not None)


def test_price_series_gap_reads_the_points_and_never_the_asset():
    """AI503-S02 — red until E-AI503: the verdict does not depend on the asset.

    The function receives the result and nothing else - no asset, no type - and the same points give the same verdict
    whichever asset they belong to.
    """
    assert list(inspect.signature(tsh.price_series_gap).parameters) == ["result"]
    for points, expected in (
        ([], "no_stored_price"),
        ([_price_point(DAY_1, "10")], None),
        ([_price_point(DAY_1, "10", currency="EUR"), _price_point(DAY_2, "11", currency="USD")], "mixed_price_currencies"),
    ):
        verdicts = {tsh.price_series_gap(FAPriceQueryResult(asset_id=asset_id, prices=points)) for asset_id in (1, 2, 3)}
        assert verdicts == {expected}, f"the same points, a different verdict by asset: {verdicts}"


# ---------------------------------------------------------------------------
# 11. E-23 - empty buckets merged into gaps, and the last value before them
# ---------------------------------------------------------------------------
#
# The contract is «E-23.2 — Il via e il contratto» in plan-phase01Email, items 1, 2, 4 and 7. A gap is a MAXIMAL run
# of contiguous empty buckets (no observed point inside) holding at least one market-open day: Monday to Friday and
# not in the holiday set. Weekends and holidays alone never make a gap. The run's buckets merge, from the first start
# to the last end. Its last value is the last observed point before its start; for a gap opening the period it is the
# seed (the last value stored before the period), or nothing when the history begins inside the period. The pure
# functions receive the holiday set; loading it is the builders' business (item 5). E-23.3 spares one trailing run, the
# snapshot day alone: section 11b.
#
# Every name E-23 adds is read from its module when the test runs (`_e23`, `_series_gap_model`), so that until E-23
# only these tests are red, never this file's collection.

#: Two weeks of March 2026, named after their weekday and their day of the month (E23-S00 pins the weekdays).
MON_2 = date(2026, 3, 2)
TUE_3 = date(2026, 3, 3)
WED_4 = date(2026, 3, 4)
THU_5 = date(2026, 3, 5)
FRI_6 = date(2026, 3, 6)
SAT_7 = date(2026, 3, 7)
SUN_8 = date(2026, 3, 8)
MON_9 = date(2026, 3, 9)
TUE_10 = date(2026, 3, 10)
WED_11 = date(2026, 3, 11)
THU_12 = date(2026, 3, 12)
#: The last value stored before a period opening on MON_2: Friday 27 February 2026, three days back.
SEED_DAY = date(2026, 2, 27)
SEED = (SEED_DAY, 9.5)
NO_HOLIDAY: frozenset[date] = frozenset()


def _e23(name: str) -> Any:
    """``technical_shared.<name>``, a name E-23 adds: until it exists this test fails, never the file's collection."""
    found = getattr(tsh, name, None)
    if found is None:
        pytest.fail(f"technical_shared.{name} does not exist: red until E-23", pytrace=False)
    return found


def _series_gap_model() -> Any:
    """``technical_payloads.SeriesGap``, the model E-23 adds, read the same way."""
    found = getattr(technical_payloads, "SeriesGap", None)
    if found is None:
        pytest.fail("technical_payloads.SeriesGap does not exist: red until E-23", pytrace=False)
    return found


def _observed(day: date, value: str, *, key: str = "close") -> ContinuousMultiOutputPoint:
    """One observed point of the period, its value under ``key``."""
    return ContinuousMultiOutputPoint(date=day, values={key: Decimal(value)})


def _daily_plan(start: date, end: date) -> BucketPlan:
    """One bucket a day, the shape of the recent daily window every plan ends with."""
    plan = BucketPlan.build(start, end, BucketingPolicy(max_bucket_days=1))
    assert all(bucket.day_count == 1 for bucket in plan.buckets)
    return plan


def _plan(*bounds: tuple[date, date]) -> BucketPlan:
    """Contiguous buckets of any width, oldest first, the shape of the older part of a compact plan."""
    buckets = tuple(Bucket(index=index, start_date=start, end_date=end) for index, (start, end) in enumerate(bounds))
    return BucketPlan(start=bounds[0][0], end=bounds[-1][1], policy=BucketingPolicy.for_detail_level(BucketDetailLevel.COMPACT), buckets=buckets)


def _gaps(points: tuple[ContinuousMultiOutputPoint, ...], plan: BucketPlan, *, key: str = "close", seed: tuple[date, float] | None = None, holidays: frozenset[date] = NO_HOLIDAY) -> list[tuple]:
    """``series_gaps`` as ``(start, end, calendar_days, last_value, last_value_date)`` rows, once its shape is checked.

    The result is a tuple (``()`` when there is no gap) of ``SeriesGap`` models.
    """
    series_gaps = _e23("series_gaps")
    series_gap = _series_gap_model()
    gaps = series_gaps(points, plan, key=key, seed=seed, holidays=holidays)
    assert isinstance(gaps, tuple), f"series_gaps returns a tuple, not a {type(gaps).__name__}"
    assert all(isinstance(gap, series_gap) for gap in gaps), gaps
    return [(gap.start_date, gap.end_date, gap.calendar_days, gap.last_value, gap.last_value_date) for gap in gaps]


def test_e23_named_days_are_the_weekdays_they_claim():
    """E23-S00 — green: every case below reads its calendar off these names, so the names must not lie."""
    named = (MON_2, TUE_3, WED_4, THU_5, FRI_6, SAT_7, SUN_8, MON_9, TUE_10, WED_11, THU_12)

    assert [day.weekday() for day in named] == [0, 1, 2, 3, 4, 5, 6, 0, 1, 2, 3]
    assert (SEED_DAY.weekday(), (MON_2 - SEED_DAY).days) == (4, 3)


def test_e23_no_price_in_period_is_the_third_reason_of_the_closed_set():
    """E23-S01 — red until E-23: ``NO_PRICE_IN_PERIOD`` is ``"no_price_in_period"``, and with the two constants of
    E-AI503 it is exactly ``PriceSeriesGapReason``: no code the builders could name that a payload refuses, and no code
    a payload accepts that the builders have no constant for.
    """
    no_price_in_period = _e23("NO_PRICE_IN_PERIOD")
    reason = technical_payloads.PriceSeriesGapReason

    assert no_price_in_period == "no_price_in_period"
    assert set(get_args(getattr(reason, "__value__", reason))) == {tsh.NO_STORED_PRICE, tsh.MIXED_PRICE_CURRENCIES, no_price_in_period}


@pytest.mark.parametrize(
    ("name", "parameters", "keyword_only"),
    [
        pytest.param("is_market_open", ["day", "holidays"], [], id="is_market_open"),
        pytest.param("series_gaps", ["points", "plan", "key", "seed", "holidays"], ["key", "seed", "holidays"], id="series_gaps"),
        pytest.param("price_series_seed", ["result"], [], id="price_series_seed"),
        pytest.param("rate_series_seed", ["rate_series", "start"], [], id="rate_series_seed"),
    ],
)
def test_e23_pure_helpers_have_the_contract_signatures(name: str, parameters: list[str], keyword_only: list[str]):
    """E23-S02 — red until E-23: the four pure helpers of contract item 7, with its parameter names, none of them async.

    ``series_gaps`` takes ``key``, ``seed`` and ``holidays`` by keyword only, as the contract writes it. None of them
    awaits anything: the holiday set is an argument (item 5), so a pure function never reaches the database for it.
    """
    function = _e23(name)
    signature = inspect.signature(function)

    assert list(signature.parameters) == parameters
    assert [param for param, spec in signature.parameters.items() if spec.kind is inspect.Parameter.KEYWORD_ONLY] == keyword_only
    assert not inspect.iscoroutinefunction(function), f"{name} must be a plain function"


@pytest.mark.parametrize(
    ("day", "holidays", "expected"),
    [
        pytest.param(MON_2, NO_HOLIDAY, True, id="monday"),
        pytest.param(FRI_6, NO_HOLIDAY, True, id="friday"),
        pytest.param(SAT_7, NO_HOLIDAY, False, id="saturday"),
        pytest.param(SUN_8, NO_HOLIDAY, False, id="sunday"),
        pytest.param(MON_9, frozenset({MON_9}), False, id="a-weekday-holiday"),
        pytest.param(MON_9, frozenset({MON_2}), True, id="a-holiday-on-another-day"),
        pytest.param(SAT_7, frozenset({SAT_7}), False, id="a-holiday-on-a-saturday"),
    ],
)
def test_e23_market_is_open_on_weekdays_that_are_not_holidays(day: date, holidays: frozenset[date], expected: bool):
    """E23-S03 — red until E-23: open means Monday to Friday and not in ``holidays``, the set it is given.

    The rule of ``market_calendar.is_market_closed_repeat`` (developer's decision of 30/09/2026), one definition of a
    market day for risk, signals and now the export. The answer is a bool, not a truthy value.
    """
    assert _e23("is_market_open")(day, holidays=holidays) is expected


@pytest.mark.parametrize(
    ("points", "plan", "seed"),
    [
        pytest.param((_observed(FRI_6, "12"), _observed(MON_9, "13")), _daily_plan(FRI_6, MON_9), None, id="between-two-prices"),
        pytest.param((_observed(MON_9, "13"), _observed(TUE_10, "13.5")), _daily_plan(SAT_7, TUE_10), (FRI_6, 12.0), id="opening-the-period"),
        pytest.param((_observed(THU_5, "11"), _observed(FRI_6, "12")), _daily_plan(THU_5, SUN_8), None, id="closing-the-period"),
    ],
)
def test_e23_a_weekend_alone_is_never_a_gap(points: tuple[ContinuousMultiOutputPoint, ...], plan: BucketPlan, seed: tuple[date, float] | None):
    """E23-S04 — red until E-23 (case 1): an empty Saturday and Sunday alone make no gap, wherever they sit.

    Between two prices; opening the period, where a seed changes nothing; closing it - an export taken on a Sunday, the
    commonest shape of all: two empty daily buckets that only say the market was closed.
    """
    assert _gaps(points, plan, seed=seed) == []


def test_e23_a_run_holding_weekdays_is_one_gap_after_the_last_observed_point():
    """E23-S05 — red until E-23 (case 2): two empty weekdays merge into one gap, Wednesday to Thursday, two days.

    Its last value is the LAST observed point before it, Tuesday's 10.5: not Monday's, not Friday's after the gap, and
    not the seed, which belongs only to a gap opening the period.
    """
    points = (_observed(MON_2, "10"), _observed(TUE_3, "10.5"), _observed(FRI_6, "12"))

    assert _gaps(points, _daily_plan(MON_2, FRI_6), seed=SEED) == [(WED_4, THU_5, 2, 10.5, TUE_3)]


@pytest.mark.parametrize(
    ("points", "plan", "expected"),
    [
        pytest.param((_observed(WED_4, "11"), _observed(WED_11, "13")), _daily_plan(WED_4, WED_11), (THU_5, TUE_10, 6, 11.0, WED_4), id="weekdays-around-a-weekend"),
        pytest.param((_observed(FRI_6, "12"), _observed(TUE_10, "13")), _daily_plan(FRI_6, TUE_10), (SAT_7, MON_9, 3, 12.0, FRI_6), id="a-weekend-then-a-weekday"),
        pytest.param((_observed(THU_5, "11"), _observed(MON_9, "13")), _daily_plan(THU_5, MON_9), (FRI_6, SUN_8, 3, 11.0, THU_5), id="a-weekday-then-a-weekend"),
    ],
)
def test_e23_empty_buckets_across_a_weekend_merge_into_one_gap(points: tuple[ContinuousMultiOutputPoint, ...], plan: BucketPlan, expected: tuple):
    """E23-S06 — red until E-23 (case 3): the run is maximal, so a weekend inside it neither splits it nor trims it.

    One gap from the first empty bucket to the last, weekend days included: Thursday to Tuesday is one gap of six days,
    and a run opening on a Saturday starts on that Saturday, not on the Monday that makes it a gap.
    """
    assert _gaps(points, plan) == [expected]


@pytest.mark.parametrize(
    ("points", "plan", "holidays", "expected"),
    [
        pytest.param((_observed(MON_2, "10"), _observed(WED_4, "11")), _daily_plan(MON_2, WED_4), frozenset({TUE_3}), [], id="a-holiday-alone"),
        pytest.param((_observed(MON_2, "10"), _observed(WED_4, "11")), _daily_plan(MON_2, WED_4), NO_HOLIDAY, [(TUE_3, TUE_3, 1, 10.0, MON_2)], id="the-same-weekday-not-a-holiday"),
        pytest.param((_observed(FRI_6, "12"), _observed(TUE_10, "13")), _daily_plan(FRI_6, TUE_10), frozenset({MON_9}), [], id="a-long-weekend"),
        pytest.param((_observed(MON_2, "10"), _observed(FRI_6, "12")), _daily_plan(MON_2, FRI_6), frozenset({TUE_3}), [(TUE_3, THU_5, 3, 10.0, MON_2)], id="a-holiday-opening-a-weekday-run"),
    ],
)
def test_e23_a_holiday_is_a_closed_day_judged_on_the_set_given(points: tuple[ContinuousMultiOutputPoint, ...], plan: BucketPlan, holidays: frozenset[date], expected: list[tuple]):
    """E23-S07 — red until E-23 (case 4): a weekday in ``holidays`` is a closed day, and only the set passed in decides.

    Alone it makes no gap, while the very same empty Tuesday with no holiday makes one. Beside a weekend it makes a long
    weekend, still no gap. Inside a run holding an open weekday it stays part of the run: the gap starts on the holiday.
    """
    assert _gaps(points, plan, holidays=holidays) == expected


@pytest.mark.parametrize(
    ("points", "plan", "seed", "expected"),
    [
        pytest.param((_observed(THU_5, "11"), _observed(FRI_6, "12")), _daily_plan(MON_2, FRI_6), SEED, (MON_2, WED_4, 3, 9.5, SEED_DAY), id="a-value-stored-before-the-period"),
        pytest.param((_observed(THU_5, "11"), _observed(FRI_6, "12")), _daily_plan(MON_2, FRI_6), None, (MON_2, WED_4, 3, None, None), id="history-beginning-inside-the-period"),
        pytest.param((_observed(TUE_10, "13"),), _daily_plan(SAT_7, TUE_10), (FRI_6, 12.0), (SAT_7, MON_9, 3, 12.0, FRI_6), id="a-period-opening-on-a-saturday"),
    ],
)
def test_e23_a_gap_opening_the_period_takes_the_seed(points: tuple[ContinuousMultiOutputPoint, ...], plan: BucketPlan, seed: tuple[date, float] | None, expected: tuple):
    """E23-S08 — red until E-23 (case 5): a gap opening the period has no observed point before it, so its last value
    is the seed, the last value stored before the period, at its own date. Without a seed - the history begins inside
    the period - the gap is still a gap, its last value and date both None (developer's decision 2).
    """
    assert _gaps(points, plan, seed=seed) == [expected]


def test_e23_a_trailing_gap_runs_to_the_end_of_the_period():
    """E23-S09 — red until E-23 (case 6): prices that stop before the end - a delisting, a broken provider - leave one
    gap from the first empty bucket to the plan's last day, weekend included, after the last observed point.
    """
    points = (_observed(MON_2, "10"), _observed(TUE_3, "10.5"))

    assert _gaps(points, _daily_plan(MON_2, SUN_8), seed=SEED) == [(WED_4, SUN_8, 5, 10.5, TUE_3)]


def test_e23_wide_empty_buckets_are_gaps_and_separate_runs_stay_separate():
    """E23-S10 — red until E-23 (case 7): a twenty-day empty bucket is a gap of twenty days, and two runs parted by a
    populated bucket are two gaps, oldest first, each after its own last observed point.

    The plan has the shape of a compact one, wide buckets first: 20, 20, 10, 3 and 2 days, then one daily bucket. The
    second run, a 3-day and a 2-day bucket (Wednesday to Sunday), merges into one gap of five days.
    """
    jan_13, jan_20, feb_1, feb_2 = date(2026, 1, 13), date(2026, 1, 20), date(2026, 2, 1), date(2026, 2, 2)
    feb_21, feb_22, feb_24 = date(2026, 2, 21), date(2026, 2, 22), date(2026, 2, 24)
    plan = _plan((jan_13, feb_1), (feb_2, feb_21), (feb_22, TUE_3), (WED_4, FRI_6), (SAT_7, SUN_8), (MON_9, MON_9))
    points = (_observed(jan_20, "18"), _observed(feb_24, "20"), _observed(MON_2, "21"), _observed(MON_9, "22"))

    assert _gaps(points, plan) == [(feb_2, feb_21, 20, 18.0, jan_20), (WED_4, SUN_8, 5, 21.0, MON_2)]


@pytest.mark.parametrize(
    ("plan", "points", "expected"),
    [
        pytest.param(_plan((MON_2, FRI_6), (SAT_7, SUN_8), (MON_9, WED_11)), (_observed(WED_4, "11"), _observed(TUE_10, "13")), [], id="a-saturday-sunday-bucket"),
        pytest.param(_plan((MON_2, SAT_7), (SUN_8, MON_9), (TUE_10, THU_12)), (_observed(FRI_6, "12"), _observed(WED_11, "13")), [(SUN_8, MON_9, 2, 12.0, FRI_6)], id="a-sunday-monday-bucket"),
    ],
)
def test_e23_a_wider_bucket_is_judged_on_every_day_inside_it(plan: BucketPlan, points: tuple[ContinuousMultiOutputPoint, ...], expected: list[tuple]):
    """E23-S11 — red until E-23: two-day buckets, as a compact plan has just before its daily window. An empty
    Saturday-Sunday bucket is no gap; an empty Sunday-Monday bucket is one, because its Monday is open, though the
    bucket starts on a Sunday.
    """
    assert _gaps(points, plan) == expected


@pytest.mark.parametrize(
    ("points", "plan", "key", "expected"),
    [
        pytest.param((_observed(MON_2, "10"), _observed(TUE_3, "10.5"), _observed(WED_4, "11")), _daily_plan(MON_2, WED_4), "close", [], id="every-daily-bucket-priced"),
        pytest.param((_observed(WED_4, "11"), _observed(MON_9, "13")), _plan((MON_2, FRI_6), (SAT_7, WED_11)), "close", [], id="every-wide-bucket-priced"),
        pytest.param((_observed(MON_2, "1.08", key="rate"), _observed(TUE_3, "1.085", key="rate"), _observed(WED_4, "1.09", key="rate")), _daily_plan(MON_2, WED_4), "rate", [], id="every-rate-bucket-observed"),
        pytest.param((_observed(MON_2, "1.08", key="rate"), _observed(WED_4, "1.09", key="rate")), _daily_plan(MON_2, WED_4), "rate", [(TUE_3, TUE_3, 1, 1.08, MON_2)], id="a-rate-gap"),
    ],
)
def test_e23_no_empty_bucket_gives_no_gap_and_the_key_names_the_value(points: tuple[ContinuousMultiOutputPoint, ...], plan: BucketPlan, key: str, expected: list[tuple]):
    """E23-S12 — red until E-23 (case 8): a series with no empty bucket gives ``()``; and ``key`` names the value read,
    so the same function serves the closes and the FX rates (``fx.rate_ohlc``, developer's decision 3), whose points
    carry no ``close`` at all.
    """
    assert _gaps(points, plan, key=key) == expected


@pytest.mark.parametrize(
    ("plan", "seed", "expected"),
    [
        pytest.param(_daily_plan(MON_2, SUN_8), SEED, [(MON_2, SUN_8, 7, 9.5, SEED_DAY)], id="a-week-of-daily-buckets"),
        pytest.param(_plan((MON_2, SUN_8)), SEED, [(MON_2, SUN_8, 7, 9.5, SEED_DAY)], id="one-wide-bucket"),
        pytest.param(_daily_plan(MON_2, SUN_8), None, [(MON_2, SUN_8, 7, None, None)], id="no-seed-either"),
        pytest.param(_daily_plan(SAT_7, SUN_8), SEED, [], id="a-period-of-one-weekend"),
    ],
)
def test_e23_a_period_without_an_observed_point_is_one_gap(plan: BucketPlan, seed: tuple[date, float] | None, expected: list[tuple]):
    """E23-S13 — red until E-23: no observed point at all - the asset whose prices are all stored before the period,
    ``no_price_in_period`` - makes the whole period one gap after the seed, when it holds an open day; a period of one
    weekend holds none. With no seed either, the rule as written still gives the gap, its last value empty.
    """
    assert _gaps((), plan, seed=seed) == expected


@pytest.mark.parametrize(
    ("result", "expected"),
    [
        pytest.param(None, None, id="no-result"),
        pytest.param(_price_result(), None, id="no-point"),
        pytest.param(_price_result(_price_point(MON_2, "9.5", days_back=3), _price_point(TUE_3, "9.5", days_back=4), _price_point(WED_4, "10")), SEED, id="carried-then-observed"),
        pytest.param(_price_result(_price_point(MON_2, "9.5", days_back=3), _price_point(TUE_3, "9.5", days_back=4)), SEED, id="only-carried-points"),
        pytest.param(_price_result(_price_point(MON_2, "10"), _price_point(TUE_3, "10", days_back=1)), None, id="observed-on-the-first-day"),
        pytest.param(_price_result(_price_point(MON_2, "10", days_back=0), _price_point(TUE_3, "11")), None, id="days-back-zero-on-the-first-day"),
    ],
)
def test_e23_price_series_seed_is_the_carried_point_opening_the_period(result: FAPriceQueryResult | None, expected: tuple[date, float] | None):
    """E23-S14 — red until E-23: the last price stored before the period, read off the point that opens ``result.prices``.

    The daily fill opens the period with a carried point exactly when a price is stored before it: its
    ``backward_fill_info.actual_rate_date`` is that price's date and its ``close`` the value, as a float (a Decimal
    would compare equal, hence the type check). An observed first point (no fill info, or ``days_back == 0``) means a
    price on the first day or a history beginning inside the period: no seed. Nothing either for no result or no point.
    """
    seed = _e23("price_series_seed")(result)

    assert seed == expected
    if expected is not None:
        assert isinstance(seed, tuple) and type(seed[0]) is date and type(seed[1]) is float, seed


def _rate(requested: date, rate: str, *, actual: date | None = None, backward_filled: bool | None = None) -> FxRateObservation:
    """One daily FX observation: observed on ``requested``, or carried from an earlier ``actual`` (flagged by default)."""
    actual_date = requested if actual is None else actual
    flagged = actual_date != requested if backward_filled is None else backward_filled
    return FxRateObservation(requested_date=requested, actual_date=actual_date, rate=Decimal(rate), backward_filled=flagged)


def _warmup_then(*period: FxRateObservation) -> FxRateSeriesResource:
    """A rate series opening on its warm-up, 25 February to 1 March, followed by ``period`` from MON_2.

    The warm-up starts with a rate carried from 20 February (so the series' first observation is a carry that is no
    seed), then quotes on Thursday 26 and Friday 27, carried over the weekend.
    """
    warmup = (
        _rate(date(2026, 2, 25), "1.05", actual=date(2026, 2, 20)),
        _rate(date(2026, 2, 26), "1.07"),
        _rate(SEED_DAY, "1.08"),
        _rate(date(2026, 2, 28), "1.08", actual=SEED_DAY),
        _rate(date(2026, 3, 1), "1.08", actual=SEED_DAY),
    )
    return FxRateSeriesResource.from_observations(warmup + period)


@pytest.mark.parametrize(
    ("rate_series", "expected"),
    [
        pytest.param(_warmup_then(_rate(MON_2, "1.08", actual=SEED_DAY), _rate(TUE_3, "1.09")), (SEED_DAY, 1.08), id="carried-on-the-first-day"),
        pytest.param(_warmup_then(_rate(MON_2, "1.08", actual=SEED_DAY, backward_filled=False), _rate(TUE_3, "1.09")), (SEED_DAY, 1.08), id="an-earlier-actual-date-without-the-flag"),
        pytest.param(_warmup_then(_rate(MON_2, "1.09"), _rate(TUE_3, "1.1")), None, id="observed-on-the-first-day"),
        pytest.param(FxRateSeriesResource.from_observations((_rate(TUE_3, "1.09"), _rate(WED_4, "1.1"))), None, id="history-beginning-inside-the-period"),
    ],
)
def test_e23_rate_series_seed_is_the_first_period_observation_when_carried(rate_series: FxRateSeriesResource, expected: tuple[date, float] | None):
    """E23-S15 — red until E-23: the FX seed is the first observation dated on or after ``start``, when it is carried
    (``backward_filled``, or an ``actual_date`` before its ``requested_date``, the negation of what
    ``observations_to_rate_points`` keeps as observed): its ``actual_date`` and its rate, as a float.

    Not the series' first observation: the series opens on its warm-up, here with a carry from 20 February that is no
    seed. An observed first day, or a history beginning inside the period, gives no seed.
    """
    seed = _e23("rate_series_seed")(rate_series, start=MON_2)

    assert seed == expected
    if expected is not None:
        assert isinstance(seed, tuple) and type(seed[0]) is date and type(seed[1]) is float, seed


@pytest.mark.parametrize(
    ("result", "expected"),
    [
        pytest.param(_price_result(_price_point(MON_2, "9.5", days_back=3), _price_point(TUE_3, "9.5", days_back=4)), "no_price_in_period", id="only-carried-points"),
        pytest.param(_price_result(_price_point(MON_2, "9.5", days_back=3)), "no_price_in_period", id="one-carried-point"),
        pytest.param(_price_result(_price_point(MON_2, "9.5", days_back=3), _price_point(TUE_3, "10")), None, id="carried-then-observed"),
        pytest.param(_price_result(_price_point(MON_2, "10"), _price_point(TUE_3, "10", days_back=1)), None, id="observed-then-carried"),
        pytest.param(_price_result(_price_point(MON_2, "9.5", days_back=3), _price_point(TUE_3, "10", days_back=0)), None, id="days-back-zero-is-an-observation"),
        pytest.param(_price_result(_price_point(MON_2, "9.5", currency="EUR", days_back=3), _price_point(TUE_3, "9.5", currency="USD", days_back=4)), "mixed_price_currencies", id="two-currencies-only-carried"),
        pytest.param(_price_result(_price_point(MON_2, "9.5", currency=None, days_back=3)), "mixed_price_currencies", id="carried-without-a-currency"),
    ],
)
def test_e23_price_series_gap_names_a_series_of_carried_points_only(result: FAPriceQueryResult, expected: str | None):
    """E23-S16 — red until E-23 for the two carried-only cases (today: None), green today for the others, which pin
    where the third code sits in the order of contract item 4.

    No point at all is ``no_stored_price`` (AI503-S01). Points not sharing one currency are ``mixed_price_currencies``,
    even when every one of them is carried. Points of one currency none of which is observed - every one with
    ``days_back > 0`` - are ``no_price_in_period``. One observed point, first or last, makes a series, whose holes are
    ``price_gaps``, not a reason; ``days_back == 0`` is an observation. The currency stays exactly when the code is
    neither of the first two: ``no_price_in_period`` keeps it. Read on the points alone, never on the asset (AI503-S02).
    """
    gap = tsh.price_series_gap(result)

    assert gap == expected, f"price_series_gap gave {gap!r}"
    assert (gap in ("no_stored_price", "mixed_price_currencies")) == (tsh.coherent_price_currency(result) is None)


# ---------------------------------------------------------------------------
# 11b. E-23.3 - a value missing on the snapshot day alone is no gap
# ---------------------------------------------------------------------------
#
# Coordinator's decision of 20/10/2026, 11:43 («E-23.3» in plan-phase01Email). A bucket plan ends on `plan.end`, the
# snapshot day: `snapshot_as_of`, the end of the exported period. A TRAILING run - the run of empty buckets that ends
# on `plan.end` - whose ONLY market-open day is `plan.end` itself is no gap: it is the snapshot day's value not
# synchronized yet, and such a gap on every asset would be noise. It is judged on `plan.end`, never on a clock, so a
# historical period ending on a weekday without a value loses that one-day gap too.
#
# Nothing else changes. A trailing run holding another open day is still one gap, merged to `plan.end` as before; a
# run that does not reach `plan.end` is a gap whatever its open days; a whole period without an observed point is one
# gap after the seed when it holds an open day besides `plan.end`; the rates (`key="rate"`) follow the same rule.
#
# No case of section 11 changes: its trailing runs (E23-S04 closing-the-period, S09, S13) all end on a Sunday, never
# open, and every other run there ends before its plan's end. Every case below passes its holiday set explicitly, and
# reads its calendar off the names E23-S00 checks.


# red until E-23.3
@pytest.mark.parametrize(
    ("points", "plan", "holidays"),
    [
        pytest.param((_observed(MON_2, "10"), _observed(TUE_3, "10.5"), _observed(WED_4, "11"), _observed(THU_5, "11.5")), _daily_plan(MON_2, FRI_6), NO_HOLIDAY, id="the-snapshot-friday-alone"),
        pytest.param((_observed(FRI_6, "12"),), _daily_plan(FRI_6, MON_9), NO_HOLIDAY, id="a-weekend-then-the-snapshot-monday"),
        pytest.param((_observed(FRI_6, "12"),), _plan((MON_2, SAT_7), (SUN_8, MON_9)), NO_HOLIDAY, id="a-sunday-monday-bucket-closing-the-period"),
        pytest.param((_observed(THU_5, "11.5"),), _daily_plan(THU_5, MON_9), frozenset({FRI_6}), id="a-holiday-friday-a-weekend-then-the-snapshot-monday"),
    ],
)
def test_e23_a_trailing_run_open_only_on_the_snapshot_day_is_no_gap(points: tuple[ContinuousMultiOutputPoint, ...], plan: BucketPlan, holidays: frozenset[date]):
    """E23-S17 — red until E-23.3: a trailing run whose only market-open day is ``plan.end`` is no gap, and the series,
    which has no other run, has none: ``()``.

    The snapshot Friday alone, after a priced Thursday; a weekend then the snapshot Monday, after a priced Friday, in
    daily buckets or as the Sunday-Monday bucket closing a compact plan (E23-S11's bucket, at the plan's end); and a
    Friday in ``holidays``, the weekend and the snapshot Monday, after a priced Thursday - the holiday is a closed day,
    so the Monday is still the run's only open day. Today each is one gap, from the run's first day to ``plan.end``,
    after the last observed point.
    """
    assert plan.end.weekday() < 5 and plan.end not in holidays, "premise: the snapshot day is a market-open weekday"

    assert _gaps(points, plan, holidays=holidays) == []


# E-23.3 barrier: green today, and after E-23.3
@pytest.mark.parametrize(
    ("points", "plan", "holidays", "expected"),
    [
        pytest.param((_observed(MON_2, "10"), _observed(TUE_3, "10.5"), _observed(WED_4, "11")), _daily_plan(MON_2, FRI_6), NO_HOLIDAY, (THU_5, FRI_6, 2, 11.0, WED_4), id="thursday-and-the-snapshot-friday"),
        pytest.param((_observed(MON_2, "10"),), _plan((MON_2, WED_4), (THU_5, FRI_6)), NO_HOLIDAY, (THU_5, FRI_6, 2, 10.0, MON_2), id="a-thursday-friday-bucket-closing-the-period"),
        pytest.param((_observed(THU_5, "11.5"),), _daily_plan(THU_5, MON_9), NO_HOLIDAY, (FRI_6, MON_9, 4, 11.5, THU_5), id="an-open-friday-a-weekend-then-the-snapshot-monday"),
        pytest.param((_observed(THU_5, "11.5"),), _daily_plan(THU_5, SUN_8), NO_HOLIDAY, (FRI_6, SUN_8, 3, 11.5, THU_5), id="an-open-friday-then-a-weekend-closing-the-period"),
    ],
)
def test_e23_a_trailing_run_with_another_open_day_stays_one_gap(points: tuple[ContinuousMultiOutputPoint, ...], plan: BucketPlan, holidays: frozenset[date], expected: tuple):
    """E23-S18 — barrier, green today and after E-23.3: a trailing run holding a market-open day other than ``plan.end``
    is still ONE gap, merged as before from its first empty bucket to ``plan.end``, the snapshot day included.

    Thursday's missing value is real, so Thursday and the snapshot Friday are one gap of two days, in daily buckets or
    in one Thursday-Friday bucket closing the plan (judged on every day inside it, not spared as the bucket of
    ``plan.end``). E23-S17's Friday-to-Monday run with that Friday open is one gap of four days: the holiday set
    decides. And one open day is not enough to be spared, it has to be ``plan.end``: an export taken on a Sunday after a
    missing Friday keeps its gap, Friday to Sunday.
    """
    assert _gaps(points, plan, holidays=holidays) == [expected]


# red until E-23.3
@pytest.mark.parametrize(
    ("points", "plan", "expected"),
    [
        pytest.param((_observed(MON_2, "10"), _observed(WED_4, "11"), _observed(THU_5, "11.5")), _daily_plan(MON_2, FRI_6), [(TUE_3, TUE_3, 1, 10.0, MON_2)], id="a-lone-tuesday-then-the-snapshot-friday"),
        pytest.param((_observed(FRI_6, "12"), _observed(TUE_10, "13.5")), _daily_plan(FRI_6, WED_11), [(SAT_7, MON_9, 3, 12.0, FRI_6)], id="a-weekend-and-its-monday-then-the-snapshot-wednesday"),
    ],
)
def test_e23_only_the_run_reaching_the_snapshot_day_is_spared(points: tuple[ContinuousMultiOutputPoint, ...], plan: BucketPlan, expected: list[tuple]):
    """E23-S19 — red until E-23.3: the rule spares only the run that ends on ``plan.end``. Each series has two runs. The
    trailing one, the snapshot day alone, is no gap. The other does not reach ``plan.end`` and stays a gap although its
    only open day is a single weekday: a lone Tuesday; or a weekend and its Monday - E23-S17's run, here followed by a
    priced Tuesday - whose only open day is the run's own last day, not the plan's. Today the trailing run is a second
    gap, after the last observed point.
    """
    assert _gaps(points, plan, holidays=NO_HOLIDAY) == expected


# E-23.3 barrier: green today, and after E-23.3
@pytest.mark.parametrize(
    ("plan", "seed", "expected"),
    [
        pytest.param(_daily_plan(MON_2, FRI_6), SEED, [(MON_2, FRI_6, 5, 9.5, SEED_DAY)], id="a-week-to-the-snapshot-friday"),
        pytest.param(_daily_plan(FRI_6, MON_9), (THU_5, 11.5), [(FRI_6, MON_9, 4, 11.5, THU_5)], id="friday-to-the-snapshot-monday"),
        pytest.param(_plan((MON_2, MON_9)), SEED, [(MON_2, MON_9, 8, 9.5, SEED_DAY)], id="one-wide-bucket-to-the-snapshot-monday"),
        pytest.param(_daily_plan(MON_2, FRI_6), None, [(MON_2, FRI_6, 5, None, None)], id="no-seed-either"),
    ],
)
def test_e23_a_period_without_an_observed_point_stays_one_gap_to_an_open_snapshot_day(plan: BucketPlan, seed: tuple[date, float] | None, expected: list[tuple]):
    """E23-S20 — barrier, green today and after E-23.3: no observed point at all - the asset with ``no_price_in_period``
    - still makes the whole period one gap after the seed when the period ends on an open weekday, because that run holds
    open days besides ``plan.end``: E23-S13, with a snapshot day that is open. Without a seed its last value stays empty.
    """
    assert plan.end.weekday() < 5, "premise: the snapshot day is a weekday"

    assert _gaps((), plan, seed=seed, holidays=NO_HOLIDAY) == expected


@pytest.mark.parametrize(
    ("points", "plan", "expected"),
    [
        # red until E-23.3: today one gap, the snapshot Friday alone, after Thursday's rate
        pytest.param(
            (_observed(MON_2, "1.08", key="rate"), _observed(TUE_3, "1.085", key="rate"), _observed(WED_4, "1.09", key="rate"), _observed(THU_5, "1.095", key="rate")),
            _daily_plan(MON_2, FRI_6),
            [],
            id="a-rate-missing-on-the-snapshot-friday",
        ),
        # red until E-23.3: today one gap, Saturday to the snapshot Monday, after Friday's rate
        pytest.param((_observed(FRI_6, "1.1", key="rate"),), _daily_plan(FRI_6, MON_9), [], id="a-weekend-then-a-rate-missing-on-the-snapshot-monday"),
        # E-23.3 barrier: green today, and after E-23.3
        pytest.param(
            (_observed(MON_2, "1.08", key="rate"), _observed(TUE_3, "1.085", key="rate"), _observed(WED_4, "1.09", key="rate")),
            _daily_plan(MON_2, FRI_6),
            [(THU_5, FRI_6, 2, 1.09, WED_4)],
            id="a-rate-missing-on-thursday-too",
        ),
    ],
)
def test_e23_the_rates_spare_the_snapshot_day_alone_too(points: tuple[ContinuousMultiOutputPoint, ...], plan: BucketPlan, expected: list[tuple]):
    """E23-S21 — red until E-23.3 for the two runs open only on the snapshot day, green today for the third: the rule
    belongs to ``series_gaps`` whatever ``key`` it reads, so the FX rates of ``fx.rate_ohlc`` (``rate_gaps``) follow it.
    A rate missing on the snapshot Friday alone, or a weekend then a rate missing on the snapshot Monday, is no gap;
    missing on Thursday too, Thursday to Friday is one gap after Wednesday's rate.
    """
    assert _gaps(points, plan, key="rate", holidays=NO_HOLIDAY) == expected
