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

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from typing import Any, get_args

import pytest
from pydantic import ValidationError

from backend.app.schemas.signals import (
    SignalAggregationProfile,
    SignalSeriesKind,
    SignalStatus,
    SignalTemporalClass,
)
from backend.app.services.ai_export.components import technical_payloads
from backend.app.services.ai_export.components.technical_payloads import (
    AssetOhlcReturnsPayload,
    AssetPriceSeriesPayload,
    FxRateOhlcPayload,
    IndicatorBucketRow,
    IndicatorOutputColumn,
    IndicatorTablePayload,
    PortfolioTechnicalPricesPayload,
    PriceBucket,
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


# ---------------------------------------------------------------------------
# E-AI503 - a held asset whose price history returns no coherent series
# ---------------------------------------------------------------------------
#
# Such an asset (no stored price up to the period end, or closes in two
# currencies) is not a series: Portfolio/Broker list it in `uncovered_assets`
# with its reason, the single Asset target carries a null currency with its
# reason. The criterion is the points the history returns, never the asset type.
#
# The new names (`AssetPriceSeriesGapPayload`) are read through the module, so
# today only the tests that use them are red, never this file's collection. And
# every rejection test first builds its VALID sibling: today `uncovered_assets`
# and `reason_code` are forbidden extra fields and a null currency is refused,
# so a bare `pytest.raises(ValidationError)` would already pass on HEAD.


@contextmanager
def _rejected_by(fragment: str) -> Iterator[None]:
    """``pytest.raises(ValidationError, match=fragment)``, with ``fragment`` in a validator's own message.

    ``match`` reads the whole error text, which also echoes the input it refused: its keys are field names, so a field
    name would match whatever the error was. A validator's message is what must name it.
    """
    with pytest.raises(ValidationError, match=fragment) as raised:
        yield
    messages = [error["msg"] for error in raised.value.errors()]
    assert any(fragment in message for message in messages), messages


def _price_bucket(**overrides) -> PriceBucket:
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
    return PriceBucket(**kwargs)


def _empty_price_bucket() -> PriceBucket:
    return _price_bucket(first=None, minimum=None, maximum=None, last=None, observation_count=0)


def _series(asset_id: int, weight: float) -> AssetPriceSeriesPayload:
    return AssetPriceSeriesPayload(asset_id=asset_id, portfolio_weight_ratio=weight, currency="USD", buckets=(_price_bucket(),), latest_close=10.5, latest_date=D3)


def _gap(asset_id: int, *, reason_code: str = "no_stored_price", weight: float | None = 0.3, **fields) -> technical_payloads.AssetPriceSeriesGapPayload:
    """An uncovered asset; ``fields`` adds E-23's ``currency``, ``last_close`` and ``last_close_date``."""
    return technical_payloads.AssetPriceSeriesGapPayload(asset_id=asset_id, portfolio_weight_ratio=weight, reason_code=reason_code, **fields)


def _prices_payload(**overrides) -> PortfolioTechnicalPricesPayload:
    """Assets 1 and 3 with a series, asset 2 uncovered: 3 eligible = 2 covered + 1 uncovered.

    The period counts leave room (a fourth asset sold inside the period, at two brokers) so that only the rule under
    test can refuse a payload.
    """
    kwargs = {
        "assets": (_series(1, 0.5), _series(3, 0.2)),
        "uncovered_assets": (_gap(2),),
        "eligible_asset_count": 3,
        "period_position_leg_count": 5,
        "period_contributor_asset_count": 4,
        "covered_asset_count": 2,
    }
    kwargs.update(overrides)
    return PortfolioTechnicalPricesPayload(**kwargs)


def _ohlc_payload(**overrides) -> AssetOhlcReturnsPayload:
    """The single target with no stored price: null currency, its reason, an empty bucket, no latest observation."""
    kwargs = {
        "asset_id": 7,
        "currency": None,
        "reason_code": "no_stored_price",
        "buckets": (_empty_price_bucket(),),
        "latest_close": None,
        "latest_date": None,
    }
    kwargs.update(overrides)
    return AssetOhlcReturnsPayload(**kwargs)


# ---------------------------------------------------------------------------
# 9. PortfolioTechnicalPricesPayload - every eligible asset is a series or a gap
# ---------------------------------------------------------------------------


def test_prices_payload_accepts_an_uncovered_asset_beside_the_series():
    """AI503-P01 — red until E-AI503: assets 1 and 3 with a series, asset 2 uncovered for ``no_stored_price``."""
    payload = _prices_payload()

    assert [asset.asset_id for asset in payload.assets] == [1, 3]
    assert [(gap.asset_id, gap.portfolio_weight_ratio, gap.reason_code) for gap in payload.uncovered_assets] == [(2, 0.3, "no_stored_price")]
    assert (payload.eligible_asset_count, payload.covered_asset_count) == (3, 2)


def test_prices_payload_rejects_a_covered_count_other_than_its_series():
    """AI503-P02 — red until E-AI503: ``covered_asset_count`` counts the series in ``assets``.

    Situation: the count is taken before the gaps are set apart, so the prompt would call an asset with no price covered.
    """
    _prices_payload()  # the valid sibling first
    with _rejected_by("covered_asset_count"):
        _prices_payload(covered_asset_count=3)


def test_prices_payload_rejects_an_eligible_count_other_than_its_series_and_gaps():
    """AI503-P03 — red until E-AI503: every eligible asset is either a series or a gap.

    Situation: an asset with no price is dropped from both lists, and the reader can no longer tell which one is missing.
    """
    _prices_payload()  # the valid sibling first
    with _rejected_by("eligible_asset_count"):
        _prices_payload(eligible_asset_count=4)


def test_prices_payload_rejects_an_asset_with_a_series_that_is_also_uncovered():
    """AI503-P04 — red until E-AI503: an asset id appears at most once across ``assets`` and ``uncovered_assets``."""
    _prices_payload()  # the valid sibling first
    with _rejected_by("at most once"):
        _prices_payload(uncovered_assets=(_gap(1),))


def test_prices_payload_rejects_an_asset_uncovered_twice():
    """AI503-P05 — red until E-AI503: an asset id appears at most once inside ``uncovered_assets``."""
    _prices_payload()  # the valid sibling first
    with _rejected_by("at most once"):
        _prices_payload(uncovered_assets=(_gap(2), _gap(2)), eligible_asset_count=4)


def test_gap_rejects_a_reason_outside_its_closed_set():
    """AI503-P06 — red until E-AI503: the reason is one of its closed set, nothing else (E23-P09 pins the set E-23 makes).

    A reason named after the asset's type is exactly what the criterion forbids: the points decide, never the type.
    """
    assert _gap(2, reason_code="mixed_price_currencies").reason_code == "mixed_price_currencies"  # the valid sibling first
    with pytest.raises(ValidationError) as raised:
        _gap(2, reason_code="crowdfund_without_prices")
    assert [error["loc"] for error in raised.value.errors()] == [("reason_code",)]


def test_prices_payload_requires_its_uncovered_assets_even_when_empty():
    """AI503-P13 — red until E-AI503: ``uncovered_assets`` is required; a fully priced universe says so with ``()``."""
    assert _prices_payload(uncovered_assets=(), eligible_asset_count=2).uncovered_assets == ()  # the valid sibling first
    with pytest.raises(ValidationError) as raised:
        PortfolioTechnicalPricesPayload(assets=(_series(1, 0.5), _series(3, 0.2)), eligible_asset_count=2, period_position_leg_count=5, period_contributor_asset_count=4, covered_asset_count=2)
    assert [(error["loc"], error["type"]) for error in raised.value.errors()] == [(("uncovered_assets",), "missing")]


# ---------------------------------------------------------------------------
# 10. AssetOhlcReturnsPayload - a null currency exactly when there is a gap
# ---------------------------------------------------------------------------


def test_ohlc_payload_accepts_a_null_currency_with_its_reason_and_an_empty_series():
    """AI503-P07 — red until E-AI503: no coherent series: null ``currency``, its ``reason_code``, every bucket empty."""
    payload = _ohlc_payload()

    assert (payload.currency, payload.reason_code) == (None, "no_stored_price")
    assert all(bucket.observation_count == 0 for bucket in payload.buckets)
    assert (payload.latest_close, payload.latest_date) == (None, None)


def test_ohlc_payload_rejects_a_null_currency_without_a_reason():
    """AI503-P08 — red until E-AI503: a null currency must say why, or the prompt could not."""
    _ohlc_payload()  # the valid sibling first
    with _rejected_by("reason_code"):
        _ohlc_payload(reason_code=None)


def test_ohlc_payload_rejects_a_reason_beside_a_currency():
    """AI503-P09 — red until E-AI503: a series with its currency has no gap to explain."""
    _ohlc_payload()  # the valid sibling first
    with _rejected_by("reason_code"):
        _ohlc_payload(currency="USD", buckets=(_price_bucket(),), latest_close=10.5, latest_date=D3)


def test_ohlc_payload_rejects_a_null_currency_beside_a_populated_bucket():
    """AI503-P10 — red until E-AI503: a populated bucket with no currency is a price the reader cannot place."""
    _ohlc_payload()  # the valid sibling first
    with _rejected_by("no bucket is populated"):
        _ohlc_payload(buckets=(_price_bucket(),))


@pytest.mark.parametrize("latest", [pytest.param({"latest_close": 10.5}, id="latest-close"), pytest.param({"latest_date": D3}, id="latest-date")])
def test_ohlc_payload_rejects_a_null_currency_beside_a_latest_observation(latest: dict):
    """AI503-P11 — red until E-AI503: with a null currency there is no latest close, nor a date for one."""
    _ohlc_payload()  # the valid sibling first
    with _rejected_by("no bucket is populated"):
        _ohlc_payload(**latest)


def test_ohlc_payload_requires_its_currency_even_when_null():
    """AI503-P12 — red until E-AI503: ``currency`` is required and nullable, not optional.

    Situation: a builder that forgets the field would otherwise export a silent null, with or without its reason.
    """
    _ohlc_payload()  # the valid sibling first
    with pytest.raises(ValidationError) as raised:
        AssetOhlcReturnsPayload(asset_id=7, reason_code="no_stored_price", buckets=(_empty_price_bucket(),))
    assert [(error["loc"], error["type"]) for error in raised.value.errors()] == [(("currency",), "missing")]


# ---------------------------------------------------------------------------
# E-23 - a series' empty buckets merged into gaps, and prices stored only before the period
# ---------------------------------------------------------------------------
#
# The contract is «E-23.2 — Il via e il contratto» in plan-phase01Email, items 1, 3 and 4. A `SeriesGap` is a run of
# empty buckets merged into one row, with the last value stored before it. `AssetPriceSeriesPayload` and
# `AssetOhlcReturnsPayload` carry theirs in `price_gaps`, `FxRateOhlcPayload` in `rate_gaps`, default `()`: in date
# order, never overlapping, never over a populated bucket. A third reason, `no_price_in_period` (prices are stored,
# none inside the period), lists the asset as uncovered with its currency and last close, and keeps the single
# target's currency.
#
# Whether a run holds an open day is not for the models to judge (they have no holiday set): `series_gaps` decides it,
# and the pure-helper tests pin that (E23-S04..S13); the models pin the shape. As for E-AI503, the new names are read
# from the module when the test runs, and every rejection builds its valid sibling first. The contract leaves the
# wording of the new rules free, so a rejection is checked with `_refused_by_a_rule`, not with a message fragment.

MAY_7 = date(2026, 5, 7)
MAY_8 = date(2026, 5, 8)
MAY_9 = date(2026, 5, 9)
MAY_10 = date(2026, 5, 10)
MAY_11 = date(2026, 5, 11)
MAY_13 = date(2026, 5, 13)
MAY_14 = date(2026, 5, 14)
MAY_17 = date(2026, 5, 17)
#: The last close stored before a period opening on D1 (Monday 4 May): Thursday 30 April.
APR_30 = date(2026, 4, 30)


def _e23_model(name: str) -> Any:
    """``technical_payloads.<name>``, a model E-23 adds: until it exists this test fails, never the file's collection."""
    found = getattr(technical_payloads, name, None)
    if found is None:
        pytest.fail(f"technical_payloads.{name} does not exist: red until E-23", pytrace=False)
    return found


def _require_e23_fields(model: Any, *names: str) -> None:
    """``model`` declares every field in ``names``: until E-23 adds them this test fails, naming them."""
    absent = [name for name in names if name not in model.model_fields]
    if absent:
        pytest.fail(f"{model.__name__} has no field {', '.join(absent)}: red until E-23", pytrace=False)


@contextmanager
def _refused_by_a_rule() -> Iterator[None]:
    """``pytest.raises(ValidationError)`` for a rule whose wording the contract leaves free.

    Today's models already refuse every E-23 payload, for a field they do not declare (``extra_forbidden``): that is
    not the rule under test, and neither is a field left out (``missing``), so the refusal must be neither. The valid
    sibling each caller builds first is what proves the fields exist.
    """
    with pytest.raises(ValidationError) as raised:
        yield
    kinds = {error["type"] for error in raised.value.errors()}
    assert not kinds & {"extra_forbidden", "missing"}, raised.value.errors()


def _gap_fields(**overrides) -> dict:
    """A valid ``SeriesGap``: Thursday 7 to Sunday 10 May, four days, after Wednesday's close of 10.5. One field overridden per test."""
    fields = {"start_date": MAY_7, "end_date": MAY_10, "calendar_days": 4, "last_value": 10.5, "last_value_date": D3}
    fields.update(overrides)
    return fields


def _series_gap(start: date, end: date, last_value: float | None = None, last_value_date: date | None = None) -> Any:
    """A valid ``SeriesGap`` from ``start`` to ``end``, its day count derived from them."""
    return _e23_model("SeriesGap")(start_date=start, end_date=end, calendar_days=(end - start).days + 1, last_value=last_value, last_value_date=last_value_date)


def _empty_bucket(start: date, end: date) -> PriceBucket:
    return _price_bucket(start_date=start, end_date=end, calendar_days=(end - start).days + 1, first=None, minimum=None, maximum=None, last=None, observation_count=0)


def _populated_bucket(start: date, end: date, value: float, *, key: str = "close") -> PriceBucket:
    return _price_bucket(start_date=start, end_date=end, calendar_days=(end - start).days + 1, first={key: value}, minimum={key: value}, maximum={key: value}, last={key: value}, observation_count=1)


def _gap_layout(key: str) -> tuple[PriceBucket, ...]:
    """Populated Mon 4-Wed 6 May, empty Thu 7-Fri 8 and Sat 9-Sun 10, populated Mon 11-Wed 13, empty Thu 14-Sun 17."""
    return (
        _populated_bucket(D1, D3, 10.5, key=key),
        _empty_bucket(MAY_7, MAY_8),
        _empty_bucket(MAY_9, MAY_10),
        _populated_bucket(MAY_11, MAY_13, 12.0, key=key),
        _empty_bucket(MAY_14, MAY_17),
    )


def _layout_gaps() -> tuple[Any, ...]:
    """The two gaps of ``_gap_layout``: each run of empty buckets merged, after the close of the bucket before it."""
    return (_series_gap(MAY_7, MAY_10, 10.5, D3), _series_gap(MAY_14, MAY_17, 12.0, MAY_13))


#: The three payloads that carry gaps (contract item 3), each with the field that holds them.
_GAP_CARRIERS: dict[str, tuple[Any, str]] = {
    "asset-price-series": (AssetPriceSeriesPayload, "price_gaps"),
    "asset-ohlc-returns": (AssetOhlcReturnsPayload, "price_gaps"),
    "fx-rate-ohlc": (FxRateOhlcPayload, "rate_gaps"),
}
_EVERY_GAP_CARRIER = pytest.mark.parametrize("kind", list(_GAP_CARRIERS))


def _carrier(kind: str, gaps: tuple[Any, ...] | None = None) -> Any:
    """A ``kind`` payload with a series over ``_gap_layout``, ``gaps`` in its gap field; ``None`` leaves the field out."""
    model, field = _GAP_CARRIERS[kind]
    _require_e23_fields(model, field)
    fields = {} if gaps is None else {field: gaps}
    if kind == "fx-rate-ohlc":
        return model(base_currency="EUR", quote_currency="USD", buckets=_gap_layout("rate"), latest_rate=12.0, latest_date=MAY_13, **fields)
    if kind == "asset-price-series":
        return model(asset_id=1, portfolio_weight_ratio=0.5, currency="USD", buckets=_gap_layout("close"), latest_close=12.0, latest_date=MAY_13, **fields)
    return model(asset_id=7, currency="USD", reason_code=None, buckets=_gap_layout("close"), latest_close=12.0, latest_date=MAY_13, **fields)


def _last_close(**overrides) -> dict:
    """The three fields of an asset with no price in the period: 9.5 USD, stored on Thursday 30 April."""
    fields = {"currency": "USD", "last_close": 9.5, "last_close_date": APR_30}
    fields.update(overrides)
    return fields


def _no_series(code: str, *, currency: str | None) -> dict:
    """``_ohlc_payload`` overrides for a target with no series: ``code`` and ``currency``, and for ``no_price_in_period``
    the gap of its whole period (Monday 4 to Wednesday 6 May, the one empty bucket) after the last close."""
    overrides: dict[str, Any] = {"reason_code": code, "currency": currency}
    if code == "no_price_in_period":
        overrides["price_gaps"] = (_series_gap(D1, D3, 9.5, APR_30),)
    return overrides


# ---------------------------------------------------------------------------
# 11. SeriesGap - one run of empty buckets, merged (E-23)
# ---------------------------------------------------------------------------


def test_e23_series_gap_accepts_a_gap_with_or_without_its_last_value():
    """E23-P01 — red until E-23: a gap of whole days with the last value before it; or with none, both null (the history
    begins inside the period: developer's decision 2); and a gap of a single day is a gap."""
    series_gap = _e23_model("SeriesGap")

    gap = series_gap(**_gap_fields())
    without = series_gap(**_gap_fields(last_value=None, last_value_date=None))
    one_day = series_gap(**_gap_fields(end_date=MAY_7, calendar_days=1))

    assert (gap.start_date, gap.end_date, gap.calendar_days, gap.last_value, gap.last_value_date) == (MAY_7, MAY_10, 4, 10.5, D3)
    assert (without.last_value, without.last_value_date) == (None, None)
    assert (one_day.start_date, one_day.end_date, one_day.calendar_days) == (MAY_7, MAY_7, 1)


@pytest.mark.parametrize(
    "override",
    [
        pytest.param({"start_date": MAY_10, "end_date": MAY_7}, id="inverted"),
        pytest.param({"calendar_days": 7}, id="more-days-than-its-range"),
        pytest.param({"calendar_days": 2}, id="its-bucket-count-instead-of-its-days"),
        pytest.param({"end_date": MAY_7, "calendar_days": 0}, id="zero-days"),
    ],
)
def test_e23_series_gap_rejects_a_day_count_that_disagrees_with_its_dates(override: dict):
    """E23-P02 — red until E-23: ``calendar_days`` is at least 1 and the inclusive day count of the gap.

    Situation: the number of merged buckets written instead of the days they span (two buckets, four days), so the
    prompt's ``days`` column would understate the hole.
    """
    series_gap = _e23_model("SeriesGap")
    series_gap(**_gap_fields())  # the valid sibling first
    with _refused_by_a_rule():
        series_gap(**_gap_fields(**override))


@pytest.mark.parametrize("override", [pytest.param({"last_value_date": None}, id="a-value-without-its-date"), pytest.param({"last_value": None}, id="a-date-without-its-value")])
def test_e23_series_gap_has_its_last_value_and_its_date_together_or_neither(override: dict):
    """E23-P03 — red until E-23: ``last_value`` and ``last_value_date`` are null together.

    Situation: a seed copied without its date, and the reader can no longer tell how old the last price is.
    """
    series_gap = _e23_model("SeriesGap")
    series_gap(**_gap_fields())  # the valid sibling first
    with _refused_by_a_rule():
        series_gap(**_gap_fields(**override))


@pytest.mark.parametrize("last_value_date", [pytest.param(MAY_7, id="on-its-first-day"), pytest.param(MAY_8, id="inside-it"), pytest.param(MAY_11, id="after-it")])
def test_e23_series_gap_last_value_is_dated_before_it(last_value_date: date):
    """E23-P04 — red until E-23: the last value comes from before the gap, so its date precedes ``start_date``.

    The day before is the valid sibling. Situation: the first price AFTER the gap taken for the last one before it,
    which would tell the reader the very price the hole hides.
    """
    series_gap = _e23_model("SeriesGap")
    series_gap(**_gap_fields())  # the valid sibling first, dated Wednesday 6 May, the day before the gap
    with _refused_by_a_rule():
        series_gap(**_gap_fields(last_value_date=last_value_date))


# ---------------------------------------------------------------------------
# 12. price_gaps / rate_gaps - the gaps a series payload carries (E-23)
# ---------------------------------------------------------------------------


@_EVERY_GAP_CARRIER
def test_e23_series_payload_gaps_default_to_empty_and_hold_ordered_gaps_over_empty_buckets(kind: str):
    """E23-P05 — red until E-23: the gap field defaults to ``()``, so every payload built today stays valid unchanged,
    and it holds a series' gaps in date order, each over empty buckets only, beside the populated ones."""
    _, field = _GAP_CARRIERS[kind]

    assert getattr(_carrier(kind), field) == ()
    gaps = getattr(_carrier(kind, _layout_gaps()), field)
    assert [(gap.start_date, gap.end_date, gap.calendar_days, gap.last_value, gap.last_value_date) for gap in gaps] == [(MAY_7, MAY_10, 4, 10.5, D3), (MAY_14, MAY_17, 4, 12.0, MAY_13)]


@_EVERY_GAP_CARRIER
def test_e23_series_payload_rejects_gaps_out_of_date_order(kind: str):
    """E23-P06 — red until E-23: gaps run oldest first.

    Situation: gaps collected per run and appended in reverse, so the PRICE GAPS table would run against BUCKETS.
    """
    gaps = _layout_gaps()
    _carrier(kind, gaps)  # the valid sibling first
    with _refused_by_a_rule():
        _carrier(kind, gaps[::-1])


@_EVERY_GAP_CARRIER
@pytest.mark.parametrize(
    ("first", "second"),
    [
        pytest.param((MAY_7, MAY_10), (MAY_9, MAY_10), id="sharing-a-bucket"),
        pytest.param((MAY_7, MAY_10), (MAY_7, MAY_10), id="the-same-gap-twice"),
    ],
)
def test_e23_series_payload_rejects_overlapping_gaps(kind: str, first: tuple[date, date], second: tuple[date, date]):
    """E23-P07 — red until E-23: two gaps never share a day, even when they start in date order.

    Situation: a run reported once whole and once again from its second bucket, so its missing days count twice.
    """
    _carrier(kind, _layout_gaps())  # the valid sibling first
    overlapping = (_series_gap(*first, 10.5, D3), _series_gap(*second, 10.5, D3))
    with _refused_by_a_rule():
        _carrier(kind, overlapping)


@_EVERY_GAP_CARRIER
@pytest.mark.parametrize(
    ("start", "end"),
    [
        pytest.param(D3, MAY_10, id="starting-on-the-last-day-of-one"),
        pytest.param(MAY_7, MAY_11, id="ending-on-the-first-day-of-one"),
        pytest.param(MAY_11, MAY_13, id="being-one"),
        pytest.param(MAY_7, MAY_17, id="spanning-one"),
    ],
)
def test_e23_series_payload_rejects_a_gap_over_a_populated_bucket(kind: str, start: date, end: date):
    """E23-P08 — red until E-23: no gap meets a populated bucket, whether by a single day or by covering it.

    Situation: gaps computed on one plan and attached to the buckets of another, so the prompt would call a priced day
    missing. The gap has no last value and is alone, so nothing but the bucket rule can refuse it.
    """
    _carrier(kind, _layout_gaps())  # the valid sibling first
    over_a_price = (_series_gap(start, end),)
    with _refused_by_a_rule():
        _carrier(kind, over_a_price)


# ---------------------------------------------------------------------------
# 13. no_price_in_period - prices are stored, none inside the period (E-23)
# ---------------------------------------------------------------------------


def test_e23_price_series_gap_reason_adds_no_price_in_period():
    """E23-P09 — red until E-23: ``PriceSeriesGapReason`` is the two codes of E-AI503 and ``no_price_in_period``, nothing else."""
    reason = technical_payloads.PriceSeriesGapReason

    assert set(get_args(getattr(reason, "__value__", reason))) == {"no_stored_price", "mixed_price_currencies", "no_price_in_period"}


def test_e23_uncovered_asset_with_no_price_in_period_carries_its_last_close():
    """E23-P10 — red until E-23: ``no_price_in_period`` carries the currency, the last close stored before the period and
    its date, the three new columns of ASSETS WITHOUT PRICE SERIES; the two other codes leave all three None, by default."""
    _require_e23_fields(technical_payloads.AssetPriceSeriesGapPayload, "currency", "last_close", "last_close_date")

    stale = _gap(2, reason_code="no_price_in_period", **_last_close())

    assert (stale.reason_code, stale.currency, stale.last_close, stale.last_close_date) == ("no_price_in_period", "USD", 9.5, APR_30)
    for code in ("no_stored_price", "mixed_price_currencies"):
        other = _gap(2, reason_code=code)
        assert (other.currency, other.last_close, other.last_close_date) == (None, None, None), code


@pytest.mark.parametrize("absent", ["currency", "last_close", "last_close_date"])
def test_e23_no_price_in_period_requires_its_currency_and_its_last_close(absent: str):
    """E23-P11 — red until E-23: ``no_price_in_period`` without its currency, its last close or that close's date is
    refused: the row would say prices are stored without the price the prompt promises to show."""
    _require_e23_fields(technical_payloads.AssetPriceSeriesGapPayload, absent)
    _gap(2, reason_code="no_price_in_period", **_last_close())  # the valid sibling first
    with _refused_by_a_rule():
        _gap(2, reason_code="no_price_in_period", **_last_close(**{absent: None}))


@pytest.mark.parametrize("code", ["no_stored_price", "mixed_price_currencies"])
@pytest.mark.parametrize(("field", "value"), [pytest.param("currency", "USD", id="currency"), pytest.param("last_close", 9.5, id="last_close"), pytest.param("last_close_date", APR_30, id="last_close_date")])
def test_e23_the_other_reasons_carry_no_currency_nor_last_close(code: str, field: str, value: object):
    """E23-P12 — red until E-23: ``no_stored_price`` and ``mixed_price_currencies`` carry none of the three - no price
    is stored, or none reads in one currency - so a value there could only be invented."""
    _require_e23_fields(technical_payloads.AssetPriceSeriesGapPayload, field)
    _gap(2, reason_code=code)  # the valid sibling first
    with _refused_by_a_rule():
        _gap(2, reason_code=code, **{field: value})


def test_e23_prices_payload_lists_an_asset_with_no_price_in_period_as_uncovered():
    """E23-P13 — red until E-23: Portfolio and Broker list such an asset among ``uncovered_assets``, with its last close,
    beside the assets with a series; ``covered_asset_count`` does not count it (developer's decision 5)."""
    _require_e23_fields(technical_payloads.AssetPriceSeriesGapPayload, "currency", "last_close", "last_close_date")

    payload = _prices_payload(uncovered_assets=(_gap(2, reason_code="no_price_in_period", **_last_close()),))

    assert [(gap.asset_id, gap.reason_code, gap.currency, gap.last_close, gap.last_close_date) for gap in payload.uncovered_assets] == [(2, "no_price_in_period", "USD", 9.5, APR_30)]
    assert (payload.covered_asset_count, payload.eligible_asset_count) == (2, 3)


def test_e23_ohlc_payload_keeps_its_currency_for_no_price_in_period():
    """E23-P14 — red until E-23: the single target whose prices are all stored before the period has ``reason_code``
    ``no_price_in_period`` and keeps its currency (the last close is read in it), every bucket empty, no latest close,
    and in ``price_gaps`` the gap of its whole period after that last close."""
    _require_e23_fields(AssetOhlcReturnsPayload, "price_gaps")

    payload = _ohlc_payload(**_no_series("no_price_in_period", currency="USD"))

    assert (payload.currency, payload.reason_code) == ("USD", "no_price_in_period")
    assert all(bucket.observation_count == 0 for bucket in payload.buckets)
    assert (payload.latest_close, payload.latest_date) == (None, None)
    assert [(gap.start_date, gap.end_date, gap.calendar_days, gap.last_value, gap.last_value_date) for gap in payload.price_gaps] == [(D1, D3, 3, 9.5, APR_30)]


@pytest.mark.parametrize(
    ("code", "currency", "refused"),
    [
        pytest.param("no_stored_price", None, "USD", id="no_stored_price"),
        pytest.param("mixed_price_currencies", None, "USD", id="mixed_price_currencies"),
        pytest.param("no_price_in_period", "USD", None, id="no_price_in_period"),
    ],
)
def test_e23_ohlc_currency_is_null_exactly_for_the_reasons_without_a_readable_price(code: str, currency: str | None, refused: str | None):
    """E23-P15 — red until E-23 for ``no_price_in_period``; green today for the other two, pinned so that E-23 keeps them.

    The currency is None exactly for ``no_stored_price`` and ``mixed_price_currencies``; ``no_price_in_period`` keeps
    it, without which its last close could not be read. Each case flips only the currency of its valid sibling.
    """
    _ohlc_payload(**_no_series(code, currency=currency))  # the valid sibling first
    flipped = _no_series(code, currency=refused)
    with _refused_by_a_rule():
        _ohlc_payload(**flipped)


@pytest.mark.parametrize(
    ("code", "currency"),
    [
        pytest.param("no_stored_price", None, id="no_stored_price"),
        pytest.param("mixed_price_currencies", None, id="mixed_price_currencies"),
        pytest.param("no_price_in_period", "USD", id="no_price_in_period"),
    ],
)
@pytest.mark.parametrize("beside", ["a-populated-bucket", "a-latest-close", "a-latest-date"])
def test_e23_ohlc_without_a_series_has_no_populated_bucket_nor_latest_close(code: str, currency: str | None, beside: str):
    """E23-P16 — red until E-23 for ``no_price_in_period``; green today for the other two (as AI503-P10/P11).

    Whatever the reason, and with a currency too, no bucket is populated and there is no latest close nor a date for
    one. The populated bucket comes after the period's gap (Thursday 7 to Saturday 9 May), so the gap rule cannot be
    what refuses it.
    """
    _ohlc_payload(**_no_series(code, currency=currency))  # the valid sibling first
    addition = {
        "a-populated-bucket": {"buckets": (_empty_price_bucket(), _populated_bucket(MAY_7, MAY_9, 10.5))},
        "a-latest-close": {"latest_close": 10.5},
        "a-latest-date": {"latest_date": D3},
    }[beside]
    refused = {**_no_series(code, currency=currency), **addition}
    with _refused_by_a_rule():
        _ohlc_payload(**refused)
