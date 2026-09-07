"""Fail-closed contract tests for the technical AI Export payload models.

`test_ai_export_components_technical.py` exercises these models through the real
`portfolio.technical_*` / `asset.*` / `fx.*` builders, which proves the happy
shapes. This file covers the rejection arms of every `model_validator` in
`components/technical_payloads.py` - the part no green build ever reaches.

Why these matter: an indicator table whose `source_nonempty_row_count` disagrees
with the rows it actually carries, or an events payload whose per-group summaries
do not reconcile with its own totals, is not a crash - it is an exported
*inconsistency* that an LLM will happily narrate as fact. These validators are
the last checkpoint, so every test below names the builder mistake it catches.

Isolation: PURE (models only, no DB/server/network).
"""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from backend.app.schemas.signals import (
    SignalAggregationProfile,
    SignalSeriesKind,
    SignalStatus,
    SignalTemporalClass,
)
from backend.app.services.ai_export.components.technical_payloads import (
    IndicatorBucketRow,
    IndicatorOutputColumn,
    IndicatorTablePayload,
    TechnicalBucket,
    TechnicalDatedValue,
    TechnicalEventBucket,
    TechnicalEventPayload,
    TechnicalEventSelectionSummary,
    TechnicalEventsPayload,
    TechnicalNumericBounds,
    TechnicalRangeValueCell,
    TechnicalSingleValueCell,
)

D1 = date(2026, 5, 4)
D2 = date(2026, 5, 5)
D3 = date(2026, 5, 6)
OUTSIDE = date(2026, 5, 20)


# ---------------------------------------------------------------------------
# Builders - valid by default, one field overridden per test
# ---------------------------------------------------------------------------


def _bucket(**overrides) -> TechnicalBucket:
    kwargs = {
        "start_date": D1,
        "end_date": D3,
        "calendar_days": 3,
        "first": {"close": 10.0},
        "minimum": {"close": 9.0},
        "maximum": {"close": 11.0},
        "last": {"close": 10.5},
        "observation_count": 3,
    }
    kwargs.update(overrides)
    return TechnicalBucket(**kwargs)


def _range_cell(**overrides) -> TechnicalRangeValueCell:
    kwargs = {
        "observation_count": 3,
        "first": TechnicalDatedValue(value=10.0, date=D1),
        "min": TechnicalDatedValue(value=9.0, date=D2),
        "max": TechnicalDatedValue(value=11.0, date=D2),
        "last": TechnicalDatedValue(value=10.5, date=D3),
    }
    kwargs.update(overrides)
    return TechnicalRangeValueCell(**kwargs)


def _column(column_key: str = "rsi") -> IndicatorOutputColumn:
    return IndicatorOutputColumn(
        column_key=column_key,
        output_key=column_key,
        semantic_id=f"signal.{column_key}",
        semantic_description=f"{column_key} output",
        unit="ratio",
        kind=SignalSeriesKind.LINE,
        aggregation_profile=SignalAggregationProfile.LAST_WITH_RANGE,
    )


def _row(**overrides) -> IndicatorBucketRow:
    kwargs = {
        "start_date": D1,
        "end_date": D3,
        "calendar_days": 3,
        "observation_count": 1,
        "cells": {"rsi": TechnicalSingleValueCell(value=55.0, date=D2)},
    }
    kwargs.update(overrides)
    return IndicatorBucketRow(**kwargs)


def _table(**overrides) -> IndicatorTablePayload:
    kwargs = {
        "instance_id": "rsi_14",
        "signal_code": "RSI",
        "temporal_class": SignalTemporalClass.FAST,
        "semantic_id": "signal.rsi",
        "semantic_description": "Relative Strength Index",
        "category": "momentum",
        "result_status": SignalStatus.OK,
        "columns": (_column(),),
        "period_summary": {"rsi": TechnicalSingleValueCell(value=55.0, date=D2)},
        "source_bucket_count": 2,
        "source_nonempty_row_count": 1,
        "rows": (_row(),),
    }
    kwargs.update(overrides)
    return IndicatorTablePayload(**kwargs)


def _event(**overrides) -> TechnicalEventPayload:
    kwargs = {
        "entity_id": "asset:7",
        "date": D2,
        "key": "rsi_overbought",
        "annotation_type": "threshold_crossing",
        "signal_code": "RSI",
        "semantic_description": "RSI crossed its overbought level",
        "values": {"value": 71.0},
    }
    kwargs.update(overrides)
    return TechnicalEventPayload(**kwargs)


def _event_bucket(**overrides) -> TechnicalEventBucket:
    kwargs = {
        "start_date": D1,
        "end_date": D3,
        "calendar_days": 3,
        "events": (_event(),),
        "event_count": 1,
    }
    kwargs.update(overrides)
    return TechnicalEventBucket(**kwargs)


def _selection_summary(**overrides) -> TechnicalEventSelectionSummary:
    kwargs = {
        "entity_id": "asset:7",
        "annotation_key": "rsi_overbought",
        "detected_count": 1,
        "recent_window_count": 1,
        "exported_count": 1,
        "selection_applied": False,
        "oldest_detected_event_date": D2,
        "newest_detected_event_date": D2,
        "oldest_exported_event_date": D2,
        "newest_exported_event_date": D2,
        "upward_count": 1,
        "downward_count": 0,
    }
    kwargs.update(overrides)
    return TechnicalEventSelectionSummary(**kwargs)


# ---------------------------------------------------------------------------
# 1. TechnicalBucket - the OHLC-style bucket shared by every continuous series
# ---------------------------------------------------------------------------


def test_technical_bucket_accepts_a_populated_and_an_explicitly_empty_bucket():
    assert _bucket().observation_count == 3
    empty = _bucket(first=None, minimum=None, maximum=None, last=None, observation_count=0)
    assert (empty.first, empty.last) == (None, None)


def test_technical_bucket_rejects_an_inverted_range():
    with pytest.raises(ValidationError, match="start_date must not follow end_date"):
        _bucket(start_date=D3, end_date=D1)


def test_technical_bucket_rejects_a_calendar_day_count_that_disagrees_with_its_dates():
    # Situation: `calendar_days` is copied from the plan's nominal bucket width
    # instead of the bucket's own inclusive range - the prompt would then report
    # a density the series does not have.
    with pytest.raises(ValidationError, match="calendar_days must match the inclusive bucket range"):
        _bucket(calendar_days=7)


def test_empty_technical_bucket_must_not_carry_values():
    # AI Export never carries a previous close forward into a gap; an empty
    # bucket with values means a synthetic observation was invented.
    with pytest.raises(ValidationError, match="empty technical buckets must not contain values"):
        _bucket(observation_count=0)


def test_populated_technical_bucket_requires_every_ohlc_field():
    with pytest.raises(ValidationError, match="populated technical buckets require first/minimum/maximum/last"):
        _bucket(minimum=None)


# ---------------------------------------------------------------------------
# 2. TechnicalRangeValueCell - complete dated statistics for one bucket cell
# ---------------------------------------------------------------------------


def test_range_cell_accepts_consistent_statistics():
    assert _range_cell().observation_count == 3


def test_range_cell_rejects_a_first_dated_after_its_last():
    # Situation: the underlying points were not sorted before aggregation.
    with pytest.raises(ValidationError, match="first date must not follow last date"):
        _range_cell(first=TechnicalDatedValue(value=10.0, date=D3), last=TechnicalDatedValue(value=10.5, date=D1))


def test_range_cell_rejects_an_inverted_min_max():
    with pytest.raises(ValidationError, match="min value must not exceed max value"):
        _range_cell(min=TechnicalDatedValue(value=20.0, date=D2), max=TechnicalDatedValue(value=5.0, date=D2))


def test_range_cell_rejects_a_first_value_outside_its_own_range():
    with pytest.raises(ValidationError, match="first value must fall inside min/max"):
        _range_cell(first=TechnicalDatedValue(value=99.0, date=D1))


def test_range_cell_rejects_a_last_value_outside_its_own_range():
    with pytest.raises(ValidationError, match="last value must fall inside min/max"):
        _range_cell(last=TechnicalDatedValue(value=99.0, date=D3))


# ---------------------------------------------------------------------------
# 3. IndicatorBucketRow - one temporal row shared by every output column
# ---------------------------------------------------------------------------


def test_indicator_row_accepts_single_and_range_cells_and_an_absent_column():
    row = _row(observation_count=3, cells={"rsi": _range_cell(), "mfi": None})
    assert row.cells["mfi"] is None


def test_indicator_row_rejects_an_inverted_range():
    with pytest.raises(ValidationError, match="start_date must not follow end_date"):
        _row(start_date=D3, end_date=D1)


def test_indicator_row_rejects_a_calendar_day_count_that_disagrees_with_its_dates():
    with pytest.raises(ValidationError, match="calendar_days must match the inclusive bucket range"):
        _row(calendar_days=10)


def test_indicator_row_rejects_a_cell_observing_more_than_the_row_itself():
    # Situation: the row count comes from the price series while a cell was
    # aggregated over the indicator's own (warm-up-inclusive) series.
    with pytest.raises(ValidationError, match="cell observation count cannot exceed row observation_count"):
        _row(observation_count=1, cells={"rsi": _range_cell()})


def test_empty_indicator_row_rejects_populated_cells_via_the_stricter_count_guard():
    # A row that says "no observations" while carrying populated cells is still
    # rejected — by the count check above, since a cell's count is always >= 1
    # (a single-value cell counts as 1, and TechnicalRangeValueCell.observation_count
    # is Field(ge=2)). `validate_bucket` used to repeat the same rule in a dedicated
    # guard that could therefore never fire; it was removed. This test is what makes
    # that removal safe: it pins the invariant, not the line that enforced it, so
    # relaxing `ge=2` some day fails here instead of silently opening a hole.
    with pytest.raises(ValidationError, match="cell observation count cannot exceed row observation_count"):
        _row(observation_count=0)


def test_empty_indicator_row_accepts_explicitly_absent_cells():
    row = _row(observation_count=0, cells={"rsi": None})
    assert row.cells["rsi"] is None


@pytest.mark.parametrize(
    "cell",
    [
        TechnicalSingleValueCell(value=55.0, date=OUTSIDE),
        TechnicalRangeValueCell(
            observation_count=2,
            first=TechnicalDatedValue(value=10.0, date=D1),
            min=TechnicalDatedValue(value=9.0, date=OUTSIDE),
            max=TechnicalDatedValue(value=11.0, date=D2),
            last=TechnicalDatedValue(value=10.5, date=D3),
        ),
    ],
    ids=["single", "range"],
)
def test_indicator_row_rejects_cell_dates_outside_the_bucket(cell):
    # Situation: warm-up observations leak past the period slice, so a cell's
    # real observation date belongs to a bucket the row does not cover.
    with pytest.raises(ValidationError, match="cell dates must fall inside the bucket"):
        _row(observation_count=3, cells={"rsi": cell})


# ---------------------------------------------------------------------------
# 4. IndicatorTablePayload - one plugin instance, its columns and its rows
# ---------------------------------------------------------------------------


def test_indicator_table_accepts_a_sampled_history():
    # Sampling is expected: fewer rendered rows than non-empty source rows.
    table = _table(source_bucket_count=5, source_nonempty_row_count=4)
    assert len(table.rows) == 1
    assert table.source_nonempty_row_count == 4


def test_indicator_table_rejects_duplicate_column_keys():
    with pytest.raises(ValidationError, match="indicator column keys must be unique"):
        _table(columns=(_column(), _column()))


def test_indicator_table_rejects_a_period_summary_that_does_not_match_its_columns():
    # Situation: a column is added without extending the whole-period summary,
    # so the table would show a column with no period-level value at all.
    with pytest.raises(ValidationError, match="period_summary must contain exactly the declared columns"):
        _table(columns=(_column(), _column("mfi")))


def test_indicator_table_rejects_more_rendered_rows_than_non_empty_source_rows():
    # Situation: the sampling counters are computed against the wrong series, so
    # the sampling manifest would understate how much history was omitted.
    with pytest.raises(ValidationError, match="rendered indicator rows cannot exceed source non-empty rows"):
        _table(source_nonempty_row_count=0, source_bucket_count=2)


def test_indicator_table_rejects_more_non_empty_rows_than_buckets():
    with pytest.raises(ValidationError, match="source non-empty rows cannot exceed source bucket count"):
        _table(source_bucket_count=1, source_nonempty_row_count=2)


def test_indicator_table_rejects_a_row_missing_a_declared_column():
    with pytest.raises(ValidationError, match="every indicator row must contain exactly the declared columns"):
        _table(rows=(_row(cells={"other": None}),))


def test_indicator_table_rejects_overlapping_or_unordered_rows():
    # Situation: rows were sampled from an unsorted collection, so the table's
    # temporal axis would run backwards.
    first = _row(start_date=D2, end_date=D3, calendar_days=2)
    second = _row(start_date=D1, end_date=D2, calendar_days=2, cells={"rsi": TechnicalSingleValueCell(value=55.0, date=D1)})
    with pytest.raises(ValidationError, match="indicator rows must be ordered and non-overlapping"):
        _table(rows=(first, second), source_nonempty_row_count=2, source_bucket_count=2)


# ---------------------------------------------------------------------------
# 5. TechnicalNumericBounds - plugin-declared axis bounds for a rendered value
# ---------------------------------------------------------------------------


def test_numeric_bounds_accept_a_one_sided_bound():
    assert TechnicalNumericBounds(minimum=0.0).maximum is None


def test_numeric_bounds_reject_an_entirely_empty_declaration():
    # An all-None bounds object carries no information; omitting the field is the
    # honest way to say "this plugin declares no axis bounds".
    with pytest.raises(ValidationError, match="require minimum and/or maximum"):
        TechnicalNumericBounds()


@pytest.mark.parametrize("minimum,maximum", [(100.0, 0.0), (50.0, 50.0)])
def test_numeric_bounds_reject_a_non_increasing_range(minimum: float, maximum: float):
    with pytest.raises(ValidationError, match="minimum must be lower than maximum"):
        TechnicalNumericBounds(minimum=minimum, maximum=maximum)


# ---------------------------------------------------------------------------
# 6. TechnicalEventBucket - selected events assigned verbatim
# ---------------------------------------------------------------------------


def test_event_bucket_accepts_an_explicitly_empty_bucket():
    assert _event_bucket(events=(), event_count=0).event_count == 0


def test_event_bucket_rejects_an_inverted_range():
    with pytest.raises(ValidationError, match="start_date must not follow end_date"):
        _event_bucket(start_date=D3, end_date=D1)


def test_event_bucket_rejects_a_calendar_day_count_that_disagrees_with_its_dates():
    with pytest.raises(ValidationError, match="calendar_days must match the inclusive bucket range"):
        _event_bucket(calendar_days=9)


def test_event_bucket_rejects_a_count_that_does_not_match_its_events():
    # Situation: the count is taken from the pre-selection group while the events
    # tuple holds the post-selection subset - the prompt would claim events it
    # does not show.
    with pytest.raises(ValidationError, match="event_count must match events"):
        _event_bucket(event_count=4)


def test_event_bucket_rejects_an_event_dated_outside_the_bucket():
    with pytest.raises(ValidationError, match="event dates must fall inside the bucket"):
        _event_bucket(events=(_event(date=OUTSIDE),))


# ---------------------------------------------------------------------------
# 7. TechnicalEventSelectionSummary - detection vs export statistics
# ---------------------------------------------------------------------------


def test_selection_summary_accepts_an_applied_selection():
    summary = _selection_summary(detected_count=5, exported_count=2, selection_applied=True, recent_window_count=2, oldest_detected_event_date=D1, newest_detected_event_date=D3, oldest_exported_event_date=D2, newest_exported_event_date=D3, upward_count=3, downward_count=2)
    assert summary.selection_applied is True


def test_selection_summary_rejects_a_recent_window_larger_than_the_detection():
    with pytest.raises(ValidationError, match="recent_window_count cannot exceed detected_count"):
        _selection_summary(recent_window_count=4)


def test_selection_summary_rejects_exporting_more_than_was_detected():
    with pytest.raises(ValidationError, match="exported_count cannot exceed detected_count"):
        _selection_summary(exported_count=4)


def test_selection_summary_rejects_a_selection_flag_that_contradicts_the_counts():
    # `selection_applied` is what tells the reader that events were omitted; a
    # false negative here hides the omission entirely.
    with pytest.raises(ValidationError, match="selection_applied must reflect whether events were omitted"):
        _selection_summary(selection_applied=True)


def test_selection_summary_rejects_an_inverted_detected_range():
    with pytest.raises(ValidationError, match="detected event date range must be chronological"):
        _selection_summary(oldest_detected_event_date=D3, newest_detected_event_date=D1, oldest_exported_event_date=D3, newest_exported_event_date=D3)


def test_selection_summary_rejects_an_inverted_exported_range():
    with pytest.raises(ValidationError, match="exported event date range must be chronological"):
        _selection_summary(detected_count=2, exported_count=2, oldest_detected_event_date=D1, newest_detected_event_date=D3, oldest_exported_event_date=D3, newest_exported_event_date=D1, recent_window_count=2, upward_count=1, downward_count=1)


def test_selection_summary_rejects_exported_dates_outside_the_detected_window():
    # Situation: the exported window is computed from a different group, so the
    # summary would claim an event older than anything actually detected.
    with pytest.raises(ValidationError, match="exported event dates must fall inside detected event dates"):
        _selection_summary(oldest_detected_event_date=D2, newest_detected_event_date=D2, oldest_exported_event_date=D1, newest_exported_event_date=D2)


def test_selection_summary_rejects_direction_counts_above_the_detection():
    with pytest.raises(ValidationError, match="direction counts cannot exceed detected_count"):
        _selection_summary(upward_count=1, downward_count=1)


# ---------------------------------------------------------------------------
# 8. TechnicalEventsPayload - buckets and summaries must reconcile
# ---------------------------------------------------------------------------


def _events_payload(**overrides) -> TechnicalEventsPayload:
    kwargs = {
        "buckets": (_event_bucket(),),
        "detected_event_count": 1,
        "exported_event_count": 1,
        "selection_summaries": (_selection_summary(),),
    }
    kwargs.update(overrides)
    return TechnicalEventsPayload(**kwargs)


def test_events_payload_accepts_a_reconciled_selection():
    payload = _events_payload(
        detected_event_count=3,
        exported_event_count=1,
        selection_summaries=(_selection_summary(detected_count=3, exported_count=1, selection_applied=True, recent_window_count=1, oldest_detected_event_date=D1, newest_detected_event_date=D3, oldest_exported_event_date=D2, newest_exported_event_date=D2, upward_count=2, downward_count=1),),
    )
    assert payload.detected_event_count == 3


def test_events_payload_rejects_a_total_that_does_not_match_its_buckets():
    # Situation: the exported total is taken before bucket assignment drops an
    # out-of-period event, so the header count and the visible events disagree.
    with pytest.raises(ValidationError, match="exported_event_count must match the events assigned to buckets"):
        _events_payload(buckets=(_event_bucket(events=(), event_count=0),))


def test_events_payload_rejects_exporting_more_than_was_detected():
    with pytest.raises(ValidationError, match="exported_event_count cannot exceed detected_event_count"):
        _events_payload(detected_event_count=0)


def test_events_payload_rejects_summaries_that_do_not_reconcile_the_detected_total():
    with pytest.raises(ValidationError, match="selection summaries must reconcile detected_event_count"):
        _events_payload(detected_event_count=2)


def test_events_payload_rejects_summaries_that_do_not_reconcile_the_exported_total():
    # detected reconciles (3 == 3) but exported does not (1 summary export vs 2 in buckets).
    with pytest.raises(ValidationError, match="selection summaries must reconcile exported_event_count"):
        _events_payload(
            buckets=(_event_bucket(events=(_event(), _event(key="other")), event_count=2),),
            detected_event_count=3,
            exported_event_count=2,
            selection_summaries=(_selection_summary(detected_count=3, exported_count=1, selection_applied=True, recent_window_count=1, oldest_detected_event_date=D1, newest_detected_event_date=D3, oldest_exported_event_date=D2, newest_exported_event_date=D2, upward_count=2, downward_count=1),),
        )


def test_events_payload_rejects_duplicate_summary_groups():
    # Two summaries for the same (entity, annotation) would double-count the
    # detection statistics the reader uses to judge completeness.
    with pytest.raises(ValidationError, match="unique by entity_id and annotation_key"):
        _events_payload(
            buckets=(_event_bucket(events=(_event(), _event(key="other")), event_count=2),),
            detected_event_count=2,
            exported_event_count=2,
            selection_summaries=(_selection_summary(), _selection_summary()),
        )
