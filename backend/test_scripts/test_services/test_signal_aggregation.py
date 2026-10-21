"""Z-29r (coordinator's decision, 19/10): the per-bucket selection rule of the signals' ``aggregation_profile`` gets one
neutral home, ``backend/app/services/signals/aggregation.py``, used by AI Export's temporal aggregators and, from Z-29s,
by the price query that reduces the signal series of the asset list's cards. Reviewer: J.

Why. Which observation stands for a bucket is decided today inside AI Export (``ai_export/temporal/aggregators.py``:
``_scalar_statistics_for_bucket``, ``select_scalar_representative``, ``select_band_envelope``) and a second time by the
chart (``frontend/src/lib/components/charts/timeSeriesAggregation.ts``: ``selectSignalRepresentative`` 341-353,
``bandRepresentative`` 375-383, the envelope 422-426). Z-29s needs it a third time in the backend; the backend gets one
home instead, in the signals' package because the profile is the signals'. The move is a pure refactor: AI Export's
outputs do not change.

The contract pinned here:

1. ``Selector = Literal["first", "last", "min", "max"]``.
2. ``SCALAR_PROFILE_SELECTORS``: a read-only ``Mapping[SignalAggregationProfile, Selector]``, exactly first_with_range
   "first", last_with_range "last", min_with_range "min", max_with_range "max", keyed by the enum's members;
   band_envelope and events_verbatim are not in it.
3. ``BAND_ENVELOPE_SELECTORS``: a read-only ``Mapping[str, Selector]``, exactly lower "min", middle "last", upper "max".
4. ``select_point(points, selector, *, value=attrgetter("value"), date=attrgetter("date"))``: the selected element of
   ``points`` itself (never a copy), None when there is none. The points are taken in date order whatever the order
   given, and the caller's list is not reordered; "first" / "last" the earliest / latest date; "min" / "max" the
   smallest / largest value, the EARLIEST date among equal values (``Decimal("2.5")`` and ``Decimal("2.50")`` are equal
   values). An unknown selector: ``ValueError``. Any element type through the keyword-only accessors: an
   ``ObservedPoint`` (Decimal values), an object with a float ``.value``, a ``(date, float)`` tuple read with
   ``date=itemgetter(0), value=itemgetter(1)``.
5. ``scalar_representative(points, profile, **accessors)``: ``select_point`` with ``SCALAR_PROFILE_SELECTORS[profile]``;
   band_envelope or events_verbatim: a ``ValueError`` naming the profile.
6. ``band_envelope(lower_points, middle_points, upper_points, **accessors)``: the 3-tuple (lower, middle, upper) of the
   elements selected per ``BAND_ENVELOPE_SELECTORS``, None for an empty component; a ``ValueError`` when two present
   selected values break lower <= middle <= upper (the present ones only, as AI Export's ``BandEnvelopeRepresentative``
   compares them).
7. One home. AI Export computes each bucket's first / minimum / maximum / last, of a scalar series and of each band
   component, through ``select_point`` and keeps its answers; it maps a scalar profile through
   ``SCALAR_PROFILE_SELECTORS`` and the envelope through ``BAND_ENVELOPE_SELECTORS``. The FORM, which is what lets a
   test see it: ``aggregators.py`` imports the module (``from backend.app.services.signals import aggregation``) and
   goes through its attributes at each call (``aggregation.select_point(...)``,
   ``aggregation.SCALAR_PROFILE_SELECTORS[...]``, ``aggregation.BAND_ENVELOPE_SELECTORS[...]``), never through a name
   imported from it nor a copy taken at import: the tests replace those three module attributes with monkeypatch (a
   spy that delegates, a spy that answers otherwise, permuted maps) and AI Export must follow them. Its dispatcher keeps
   ``_SCALAR_AGGREGATION_PROFILES`` (an existing test patches it), equal to the map's keys.
8. Outputs unchanged: on every case of the table, AI Export's statistics, representatives and envelope equal the
   module's answers — checked against today's AI Export (the old rule) as much as after the move.

The table (``_SCALAR_CASES``, ``_BAND_CASES_CHART``, ``_BAND_CASES_PARTIAL``, ``_BAND_BREAKS_IN_A_ROW``,
``_BAND_BREAKS_ACROSS_DAYS``) names each case's expected element by its day, as the chart's rule picks it: ties,
unsorted input, negative values, a single point, empty, plus the cases the chart's own Vitest asserts
(``timeSeriesAggregation.test.ts``: the weekly line 362-380, the weekly Bollinger band 382-414, the Drawdown trough
440-459). The shared fixture both stacks read (``backend/test_scripts/fixtures/signals/aggregation_profiles.v1.json``,
which that Vitest runs through ``selectSignalRepresentative`` at 474-483) is checked as well. SAG-T01…T03 hold the table
against a line-by-line transcription of the TypeScript, so it cannot drift from the chart.

Dates are unique within a series: equal dates are outside the contract. One existing AI Export test feeds three points
on one date all the same (``test_ai_export_temporal.py::test_ohlc_first_min_max_last_and_observation_count``: the order
given breaks the tie, first the first given and last the last given, as a stable sort — and the chart's
``[...points].sort`` — keeps it). For it to stay green once AI Export goes through ``select_point``, ``select_point``
must keep that order: sorted by date, then the first / the last element; not ``max(points, key=date)``, which answers
the first of the latest.

Isolation: PURE. No lane database, no server, no network: pure functions over points built in memory, AI Export's
aggregators called on hand-built plans, the replaced module attributes put back by monkeypatch, the shared fixture read
from the repository.

Red at HEAD 14247474e (before Z-29r), each for the reason its docstring gives: every SAG-M, SAG-P, SAG-E and SAG-A test
fails at ``_aggregation()`` — ``backend.app.services.signals.aggregation`` does not exist. With the module written and
AI Export not yet moved, SAG-A01…A06 stay red (AI Export never calls the module and ignores its maps) while SAG-A07…A10
pass (today's AI Export already agrees with the rule: the move must keep it so). Green then, written green:
SAG-T01…T03 (they pin the table against the TypeScript, not the code).

Z-29s-a (contract of 20/10 on 5bbadda95, coordinator's lot; developer's Q-Z29-2 of 19/10): a sampled card's signal
series are reduced by the backend as the chart would reduce them, each output by its own ``aggregation_profile``. The
module gains ``sample_signal_series(series, profile, resolution, render_dates)``, pure, pinned here (SAG-S):

9. ``render_dates`` are the sampled price dates, ascending, one per bucket (``price_sampling.sample_dates``: the last day
   of each ISO week or calendar month, the last one cut at the range's end). A point belongs to its own date's bucket; a
   point whose bucket has no render date is dropped. Daily: the series itself, unchanged.
10. A line or an area with a scalar profile is reduced run by run, as ``backendRenderer.ts`` (``renderScalarSeries``)
    splits it before ``downsampleRenderedSignal`` reduces each run: a run is a stretch of points with a value, ended by
    a point without one; leading and trailing nulls belong to no run and are dropped; a date absent is no gap. Per run
    and bucket the representative is ``select_point``'s element itself, re-dated at the render date (a calendar-return
    point keeps its ``provenance``; min / max ties the earliest's). Between two runs that both gave points, one marker
    ``SignalValuePoint(date=d, value=None)``, ``d`` the earlier run's last representative's date + 1 day, only when ``d``
    is before the later run's first representative's date; two runs with a representative in the same bucket keep the
    later run's alone (residue R1), and two representatives on consecutive days get no marker (residue R3).
11. A bar: its nulls dropped, one representative per bucket, no run, no marker. A band with ``band_envelope``: per
    bucket over its complete points only, one ``SignalBandPoint`` (the lowest lower, the last middle, the highest upper);
    a bucket without one gives none.
12. A reduction that would leave no value: the series unchanged. A profile that does not fit the kind (``band_envelope``
    on a scalar, a scalar profile on a band, ``events_verbatim``): ``ValueError``, as the chart throws. The result is the
    series' own class, every field but ``points`` unchanged; the caller's series is not changed.

The case table ``backend/test_scripts/fixtures/signals/signal_sampling_cases.v1.json`` holds the cases both stacks read:
every case through ``sample_signal_series`` here (SAG-S02), the ``browser_parity`` ones through
``downsampleRenderedSignal`` in ``timeSeriesAggregation.test.ts`` (each run apart, the expected split at its markers);
its non-parity cases are the residues R1 and R3 and one synthetic input, each said in its note.

Red at 5bbadda95 (before Z-29s-a), each for the reason its docstring gives: SAG-S02…S08 fail at ``_sampler()`` —
``sample_signal_series`` does not exist. It is read from the module at the call, never imported at the top, so that the
26 tests above still collect and pass. Green then, written green: SAG-S01 (it pins the table, not the code).
"""

from __future__ import annotations

import collections
import dataclasses
import functools
import importlib
import itertools
import json
import re
import typing
from collections.abc import Callable, Mapping, MutableMapping, Sequence
from datetime import date, timedelta
from decimal import Decimal
from operator import attrgetter, itemgetter
from pathlib import Path
from types import MappingProxyType, ModuleType

import pytest

from backend.app.schemas.signals import (
    SignalAggregationProfile,
    SignalAreaSeries,
    SignalAxisRole,
    SignalAxisSpec,
    SignalBandPoint,
    SignalBandSeries,
    SignalBarSeries,
    SignalCalendarReturnPointStatus,
    SignalCalendarReturnProvenance,
    SignalCalendarReturnValuePoint,
    SignalColorRole,
    SignalLinePattern,
    SignalLineSeries,
    SignalOutputStyle,
    SignalReferenceLevel,
    SignalRegionLineStyle,
    SignalUnit,
    SignalValuePoint,
    SignalValueRegion,
    SignalViewTransform,
)
from backend.app.services.ai_export.temporal.aggregators import (
    ScalarBucketStatistics,
    aggregate_band_statistics,
    aggregate_scalar_statistics,
    aggregate_signal_buckets,
    select_band_envelope,
    select_scalar_representative,
)
from backend.app.services.ai_export.temporal.plan import Bucket, BucketPlan
from backend.app.services.ai_export.temporal.points import BandObservedPoint, ObservedPoint
from backend.app.services.ai_export.temporal.policy import BucketingPolicy

AGGREGATION_MODULE = "backend.app.services.signals.aggregation"
#: The module's public names (the contract, points 1-6).
PUBLIC = ("Selector", "SCALAR_PROFILE_SELECTORS", "BAND_ENVELOPE_SELECTORS", "select_point", "scalar_representative", "band_envelope")
SELECTORS = ("first", "last", "min", "max")
BAND_COMPONENTS = ("lower", "middle", "upper")
#: The contract's maps, written here and not read from the module: each profile's selector as selectSignalRepresentative
#: applies it (timeSeriesAggregation.ts:344-351), each component's as the chart's envelope does (:422-424).
PROFILE_SELECTORS = {
    SignalAggregationProfile.FIRST_WITH_RANGE: "first",
    SignalAggregationProfile.LAST_WITH_RANGE: "last",
    SignalAggregationProfile.MIN_WITH_RANGE: "min",
    SignalAggregationProfile.MAX_WITH_RANGE: "max",
}
ENVELOPE_SELECTORS = {"lower": "min", "middle": "last", "upper": "max"}
NOT_SCALAR = (SignalAggregationProfile.BAND_ENVELOPE, SignalAggregationProfile.EVENTS_VERBATIM)
#: The fixture both stacks read: timeSeriesAggregation.test.ts:474-483 (Vitest) and test_ai_export_temporal.py.
SHARED_FIXTURE = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "signals" / "aggregation_profiles.v1.json").read_text(encoding="utf-8"))

_VALUE = attrgetter("value")
_DATE = attrgetter("date")


# =============================================================================
# HELPERS
# =============================================================================


def _aggregation(*names: str) -> ModuleType:
    """The one home, imported at the call: while it is missing, each test asking it fails saying so and the file still
    collects; a member a test needs and the module lacks fails the same way, named."""
    try:
        module = importlib.import_module(AGGREGATION_MODULE)
    except ModuleNotFoundError as missing:
        if missing.name != AGGREGATION_MODULE:
            raise
    else:
        absent = [name for name in names if not hasattr(module, name)]
        if not absent:
            return module
        pytest.fail(f"{AGGREGATION_MODULE} has no {', '.join(absent)} (Z-29r's contract: {', '.join(PUBLIC)})")
    pytest.fail(f"{AGGREGATION_MODULE} does not exist: Z-29r's one home of the aggregation_profile rule ({', '.join(PUBLIC)})")


def _day(day: int) -> date:
    """A day of January 2026 (the 5th a Monday, as in the chart's Vitest)."""
    return date(2026, 1, day)


def _decimal(raw: str | None) -> Decimal | None:
    return None if raw is None else Decimal(raw)


@dataclasses.dataclass(frozen=True, slots=True, eq=False)
class _Reading:
    """A float reading behind ``.date`` / ``.value``. No ``__eq__``: only identity finds it again."""

    date: date
    value: float


def _observed(day: date, raw: str) -> ObservedPoint:
    return ObservedPoint(date=day, value=Decimal(raw))


def _reading(day: date, raw: str) -> _Reading:
    return _Reading(date=day, value=float(raw))


def _float_tuple(day: date, raw: str) -> tuple[date, float]:
    return (day, float(raw))


#: The element types the module serves through its accessors: how to build one from (day, value as written), and the
#: accessors to pass for it (none: the defaults read ``.date`` / ``.value``).
KINDS: dict[str, tuple[Callable[[date, str], object], dict[str, Callable[[object], object]]]] = {
    "observed-point-decimal": (_observed, {}),
    "object-float": (_reading, {}),
    "tuple-float-itemgetter": (_float_tuple, {"date": itemgetter(0), "value": itemgetter(1)}),
}


def _picked(points: Sequence[object], answer: object, date_of: Callable[[object], date] = _DATE) -> int | str | None:
    """The day of ``answer`` when it IS one of ``points`` (identity), None for None, else what it is instead."""
    if answer is None:
        return None
    if not any(point is answer for point in points):
        return f"not one of the given elements (a copy, or a stranger): {answer!r}"
    return date_of(answer).day


def _components(rows: Sequence[tuple], build: Callable[[date, str], object]) -> dict[str, list[object]]:
    """A band's three component series from its rows (day, lower, middle, upper): an absent (None) value skipped, the
    rows' order kept."""
    return {name: [build(_day(row[0]), row[position]) for row in rows if row[position] is not None] for position, name in enumerate(BAND_COMPONENTS, start=1)}


def _band_points(rows: Sequence[tuple]) -> list[BandObservedPoint]:
    """The same rows as AI Export's band observations."""
    return [BandObservedPoint(date=_day(day), lower=_decimal(lower), middle=_decimal(middle), upper=_decimal(upper)) for day, lower, middle, upper in rows]


def _plan(*bounds: tuple[int, int]) -> BucketPlan:
    """A contiguous plan of these buckets, each (first day, last day) of January 2026."""
    buckets = tuple(Bucket(index=index, start_date=_day(first), end_date=_day(last)) for index, (first, last) in enumerate(bounds))
    return BucketPlan(
        start=buckets[0].start_date,
        end=buckets[-1].end_date,
        policy=BucketingPolicy(max_bucket_days=max(bucket.day_count for bucket in buckets)),
        buckets=buckets,
    )


def _read(statistic: object) -> tuple[int, str] | None:
    """One of AI Export's ``DatedValue`` as (day, value as written)."""
    return None if statistic is None else (statistic.observed_date.day, str(statistic.value))


def _read_point(point: object) -> tuple[int, str] | None:
    """An ``ObservedPoint`` the module answered as (day, value as written)."""
    return None if point is None else (point.date.day, str(point.value))


def _reads(statistics: ScalarBucketStatistics) -> dict[str, tuple[int, str] | None]:
    """AI Export's four statistics of one bucket, by the selector that names them."""
    return {"first": _read(statistics.first), "last": _read(statistics.last), "min": _read(statistics.minimum), "max": _read(statistics.maximum)}


def _days(reads: Mapping[str, tuple[int, str] | None]) -> dict[str, int | None]:
    return {name: None if read is None else read[0] for name, read in reads.items()}


def _payload(point: object) -> dict[str, str] | None:
    """An ``ObservedPoint`` in the shared fixture's shape."""
    return None if point is None else {"value": format(point.value, "f"), "date": point.date.isoformat()}


# =============================================================================
# THE TABLE — WHAT THE CHART'S RULE PICKS
# =============================================================================

#: (the points as given: (day, value); the expected day per selector), as the chart's rule picks them:
#: selectSignalRepresentative, timeSeriesAggregation.ts:341-353 — none for no point (:342), sorted by date (:343), first
#: the earliest (:344), last the latest (:345), min / max a strict reduce from the earliest, so that a later equal value
#: never replaces it (:346-351).
_SCALAR_CASES = [
    pytest.param((), {"first": None, "last": None, "min": None, "max": None}, id="empty"),
    pytest.param(((8, "9.5"),), {"first": 8, "last": 8, "min": 8, "max": 8}, id="single-point"),
    pytest.param(((8, "20"), (5, "15"), (7, "5"), (6, "25")), {"first": 5, "last": 8, "min": 7, "max": 6}, id="unsorted-distinct"),
    # the later of two equal minima given first: the order given would pick day 9
    pytest.param(((9, "5"), (5, "9"), (7, "5"), (8, "6")), {"first": 5, "last": 9, "min": 7, "max": 5}, id="tied-minima-the-later-given-first"),
    # three equal maxima, the latest given first
    pytest.param(((9, "8"), (6, "8"), (5, "1"), (7, "8")), {"first": 5, "last": 9, "min": 5, "max": 6}, id="tied-maxima-the-latest-given-first"),
    pytest.param(((7, "4"), (5, "4"), (6, "4")), {"first": 5, "last": 7, "min": 5, "max": 5}, id="all-equal-unsorted"),
    # Decimal("2.50") == Decimal("2.5"), Decimal("3.000") == Decimal("3"): the earliest element, not the first written
    pytest.param(((7, "2.50"), (5, "2.5"), (8, "3.000"), (6, "3")), {"first": 5, "last": 8, "min": 5, "max": 6}, id="equal-values-written-differently"),
    # timeSeriesAggregation.test.ts:362-380, the weekly line (the points of its bucket 01-05…01-11): last keeps day 9
    pytest.param(((5, "1"), (6, "2"), (9, "3")), {"first": 5, "last": 9, "min": 5, "max": 9}, id="vitest-weekly-line"),
    # timeSeriesAggregation.test.ts:440-459, the Drawdown trough: min_with_range keeps -20, day 6
    pytest.param(((5, "0"), (6, "-20"), (9, "-5")), {"first": 5, "last": 9, "min": 6, "max": 5}, id="vitest-drawdown-trough-negative"),
    pytest.param(((9, "-7.5"), (8, "-0.5"), (5, "-7.5"), (7, "-3"), (6, "-0.5")), {"first": 5, "last": 9, "min": 5, "max": 6}, id="negative-ties-unsorted"),
]

#: (the rows as given: (day, lower, middle, upper); the expected day per component), every component on every row: the
#: chart's rule, bandRepresentative (timeSeriesAggregation.ts:375-383) asked lower 'min', middle 'last', upper 'max'
#: (:422-424) — its candidates sorted by date (:376), the latest for 'last' (:378), a strict reduce from the earliest for
#: 'min' / 'max' (:379-382).
_BAND_CASES_CHART = [
    pytest.param(((5, "1", "2", "3"),), {"lower": 5, "middle": 5, "upper": 5}, id="single-row"),
    # timeSeriesAggregation.test.ts:382-414, the weekly Bollinger band (the rows of its bucket 01-05…01-11)
    pytest.param(((5, "90", "100", "110"), (6, "89", "101", "112"), (9, "92", "105", "111")), {"lower": 6, "middle": 9, "upper": 6}, id="vitest-weekly-bollinger"),
    pytest.param(((9, "1", "4", "9"), (5, "1", "3", "9"), (7, "2", "5", "7")), {"lower": 5, "middle": 9, "upper": 5}, id="unsorted-tied-lower-and-upper"),
    pytest.param(((7, "-6", "-2", "-1"), (5, "-5", "-3", "-1"), (6, "-6", "-4", "-2")), {"lower": 6, "middle": 7, "upper": 5}, id="negative-ties-unsorted"),
    # lower == middle == upper is an envelope: the chart throws on a strict > only (:425)
    pytest.param(((6, "5", "5", "5"), (5, "5", "5", "5")), {"lower": 5, "middle": 6, "upper": 5}, id="flat-band"),
]

#: A component absent on some or every day: AI Export's band (``BandObservedPoint`` takes any of the three), which the
#: chart never aggregates (its band arrays are aligned, :391-399, and it skips an empty bucket, :421). The module answers
#: None for a component never observed.
_BAND_CASES_PARTIAL = [
    pytest.param(((5, "1", None, "9"), (6, "0", None, "8")), {"lower": 6, "middle": None, "upper": 5}, id="middle-never-observed"),
    pytest.param(((5, None, "3", None), (6, None, "4", None)), {"lower": None, "middle": 6, "upper": None}, id="only-the-middle"),
    pytest.param((), {"lower": None, "middle": None, "upper": None}, id="empty"),
]

_BAND_CASES = [*_BAND_CASES_CHART, *_BAND_CASES_PARTIAL]

#: The envelope the chart refuses (timeSeriesAggregation.ts:425-426: lower > middle or middle > upper), from a row whose
#: own components are out of order: only the chart can be given one (``BandObservedPoint`` refuses it).
_BAND_BREAKS_IN_A_ROW = [
    pytest.param(((5, "10", "5", "20"),), id="lower-above-middle"),
    pytest.param(((5, "1", "30", "20"),), id="middle-above-upper"),
]

#: The same refusal between components observed on different days, each row in order: AI Export's
#: ``BandEnvelopeRepresentative`` refuses them too, comparing the components present.
_BAND_BREAKS_ACROSS_DAYS = [
    pytest.param(((5, "10", None, None), (6, None, None, "5")), id="no-middle-lower-above-upper"),
    pytest.param(((5, "10", None, None), (6, None, "5", None)), id="no-upper-lower-above-middle"),
    pytest.param(((5, None, "10", None), (6, None, None, "5")), id="no-lower-middle-above-upper"),
    pytest.param(((5, "10", None, "20"), (6, None, "5", None)), id="all-present-lower-above-middle"),
]


# =============================================================================
# SAG-M — THE MODULE'S SURFACE
# =============================================================================


def test_sag_m01_selector_is_the_literal_of_the_four_selections():
    """SAG-M01: ``Selector`` is the ``Literal`` of "first", "last", "min" and "max".

    Red before Z-29r: ``backend.app.services.signals.aggregation`` does not exist.
    """
    selector = _aggregation("Selector").Selector
    selector = getattr(selector, "__value__", selector)  # a ``type`` alias holds its Literal there
    assert typing.get_origin(selector) is typing.Literal, f"Selector is {selector!r}, not a Literal"
    assert set(typing.get_args(selector)) == set(SELECTORS)


def _assert_read_only(mapping: object, new_key: object, existing_key: object) -> None:
    """A mapping nobody can change: not a MutableMapping (checked first, so that a plain dict is refused before anything
    is written into it), an assignment or a deletion raising TypeError and leaving it as it was."""
    assert isinstance(mapping, Mapping), f"{type(mapping).__name__} is not a Mapping"
    assert not isinstance(mapping, MutableMapping), f"{type(mapping).__name__} can be changed: a read-only mapping expected (a MappingProxyType, say)"
    before = dict(mapping)
    with pytest.raises(TypeError):
        mapping[new_key] = "max"
    with pytest.raises(TypeError):
        mapping[existing_key] = "max"
    with pytest.raises(TypeError):
        del mapping[existing_key]
    assert dict(mapping) == before


def test_sag_m02_scalar_profile_selectors_map_exactly_the_four_scalar_profiles():
    """SAG-M02: ``SCALAR_PROFILE_SELECTORS`` is exactly first_with_range "first", last_with_range "last", min_with_range
    "min", max_with_range "max", keyed by ``SignalAggregationProfile`` members, without band_envelope and
    events_verbatim, and read-only.

    Red before Z-29r: ``backend.app.services.signals.aggregation`` does not exist.
    """
    mapping = _aggregation("SCALAR_PROFILE_SELECTORS").SCALAR_PROFILE_SELECTORS
    assert dict(mapping) == PROFILE_SELECTORS
    assert all(type(profile) is SignalAggregationProfile for profile in mapping), f"keys {list(mapping)!r}: not SignalAggregationProfile members"
    assert not set(NOT_SCALAR) & set(mapping)
    _assert_read_only(mapping, SignalAggregationProfile.BAND_ENVELOPE, SignalAggregationProfile.FIRST_WITH_RANGE)


def test_sag_m03_band_envelope_selectors_map_lower_min_middle_last_upper_max():
    """SAG-M03: ``BAND_ENVELOPE_SELECTORS`` is exactly lower "min", middle "last", upper "max" (the chart's envelope,
    timeSeriesAggregation.ts:422-424), and read-only.

    Red before Z-29r: ``backend.app.services.signals.aggregation`` does not exist.
    """
    mapping = _aggregation("BAND_ENVELOPE_SELECTORS").BAND_ENVELOPE_SELECTORS
    assert dict(mapping) == ENVELOPE_SELECTORS
    _assert_read_only(mapping, "outer", "lower")


def test_sag_m04_the_accessors_are_keyword_only():
    """SAG-M04: the accessors are given by name, never by position: ``select_point(points, selector, *, value, date)``,
    ``scalar_representative(points, profile, **accessors)``, ``band_envelope(lower, middle, upper, **accessors)``.

    Red before Z-29r: ``backend.app.services.signals.aggregation`` does not exist.
    """
    aggregation = _aggregation("select_point", "scalar_representative", "band_envelope")
    points = [(_day(5), 1.0), (_day(6), 2.0)]
    by_position = (itemgetter(1), itemgetter(0))
    with pytest.raises(TypeError):
        aggregation.select_point(points, "first", *by_position)
    with pytest.raises(TypeError):
        aggregation.scalar_representative(points, SignalAggregationProfile.FIRST_WITH_RANGE, *by_position)
    with pytest.raises(TypeError):
        aggregation.band_envelope(points, points, points, *by_position)


# =============================================================================
# SAG-P — THE MODULE PICKS AS THE CHART
# =============================================================================


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize(("given", "expected"), _SCALAR_CASES)
def test_sag_p01_select_point_picks_as_the_chart(given, expected, kind):
    """SAG-P01: for each selector ``select_point`` answers the element the chart's rule picks (the table), that element
    itself, and leaves the caller's list in its order; for an ``ObservedPoint``, a float object and a tuple read through
    itemgetter alike.

    Red before Z-29r: ``backend.app.services.signals.aggregation`` does not exist.
    """
    aggregation = _aggregation("select_point")
    build, accessors = KINDS[kind]
    points = [build(_day(day), raw) for day, raw in given]
    order = [id(point) for point in points]
    picked = {selector: _picked(points, aggregation.select_point(points, selector, **accessors), accessors.get("date", _DATE)) for selector in SELECTORS}
    assert [id(point) for point in points] == order, "select_point reordered the caller's list"
    assert picked == expected


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize(("given", "expected"), _SCALAR_CASES)
def test_sag_p02_scalar_representative_picks_as_select_signal_representative(given, expected, kind):
    """SAG-P02: for each of the four scalar profiles ``scalar_representative`` answers the element
    ``selectSignalRepresentative`` gives for that profile (timeSeriesAggregation.ts:341-353), the accessors passed on.

    Red before Z-29r: ``backend.app.services.signals.aggregation`` does not exist.
    """
    aggregation = _aggregation("scalar_representative")
    build, accessors = KINDS[kind]
    points = [build(_day(day), raw) for day, raw in given]
    picked = {profile.value: _picked(points, aggregation.scalar_representative(points, profile, **accessors), accessors.get("date", _DATE)) for profile in PROFILE_SELECTORS}
    assert picked == {profile.value: expected[selector] for profile, selector in PROFILE_SELECTORS.items()}


@pytest.mark.parametrize("case", SHARED_FIXTURE["scalar_cases"], ids=lambda case: case["id"])
def test_sag_p03_the_shared_fixture_scalar_cases(case):
    """SAG-P03: on the scalar cases both stacks read (``aggregation_profiles.v1.json``, which the Vitest runs through
    ``selectSignalRepresentative``, timeSeriesAggregation.test.ts:474-483), ``select_point`` gives the expected first /
    min / max / last and ``scalar_representative`` the expected representative of each profile.

    Red before Z-29r: ``backend.app.services.signals.aggregation`` does not exist.
    """
    aggregation = _aggregation("select_point", "scalar_representative")
    points = [ObservedPoint(date=date.fromisoformat(point["date"]), value=Decimal(point["value"])) for point in case["points"]]
    expected = case["expected"]
    assert {selector: _payload(aggregation.select_point(points, selector)) for selector in SELECTORS} == {selector: expected[selector] for selector in SELECTORS}
    assert {profile: _payload(aggregation.scalar_representative(points, SignalAggregationProfile(profile))) for profile in expected["representatives"]} == expected["representatives"]


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize(("rows", "expected"), _BAND_CASES)
def test_sag_p04_band_envelope_picks_as_the_chart(rows, expected, kind):
    """SAG-P04: ``band_envelope`` answers the 3-tuple of the elements the chart's envelope picks — lower the earliest
    minimum, middle the latest, upper the earliest maximum (timeSeriesAggregation.ts:375-383, 422-424) — each the element
    itself, None for a component never observed; for the three element kinds alike.

    Red before Z-29r: ``backend.app.services.signals.aggregation`` does not exist.
    """
    aggregation = _aggregation("band_envelope")
    build, accessors = KINDS[kind]
    components = _components(rows, build)
    answer = aggregation.band_envelope(*components.values(), **accessors)
    assert isinstance(answer, tuple) and len(answer) == 3, f"band_envelope answered {answer!r}: the 3-tuple (lower, middle, upper) expected"
    date_of = accessors.get("date", _DATE)
    assert {name: _picked(components[name], selected, date_of) for name, selected in zip(BAND_COMPONENTS, answer, strict=True)} == expected


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("rows", [*_BAND_BREAKS_IN_A_ROW, *_BAND_BREAKS_ACROSS_DAYS])
def test_sag_p05_band_envelope_refuses_a_broken_envelope(rows, kind):
    """SAG-P05: ``band_envelope`` raises ValueError when two present selected values break lower <= middle <= upper: the
    chart's refusal (timeSeriesAggregation.ts:425-426) of a row out of order, and the same between components observed
    on different days, an absent component skipped (AI Export's ``BandEnvelopeRepresentative``).

    Red before Z-29r: ``backend.app.services.signals.aggregation`` does not exist.
    """
    aggregation = _aggregation("band_envelope")
    build, accessors = KINDS[kind]
    with pytest.raises(ValueError):
        aggregation.band_envelope(*_components(rows, build).values(), **accessors)


def test_sag_p06_the_shared_fixture_band_case():
    """SAG-P06: on the band case of ``aggregation_profiles.v1.json``, ``select_point`` gives each component's expected
    first / min / max / last and ``band_envelope`` the expected envelope.

    Red before Z-29r: ``backend.app.services.signals.aggregation`` does not exist.
    """
    aggregation = _aggregation("select_point", "band_envelope")
    case = SHARED_FIXTURE["band_case"]
    expected = case["expected"]
    components = {name: [ObservedPoint(date=date.fromisoformat(point["date"]), value=Decimal(point[name])) for point in case["points"]] for name in BAND_COMPONENTS}
    for name, points in components.items():
        assert {selector: _payload(aggregation.select_point(points, selector)) for selector in SELECTORS} == {selector: expected[name][selector] for selector in SELECTORS}, name
    envelope = aggregation.band_envelope(*components.values())
    assert {name: _payload(selected) for name, selected in zip(BAND_COMPONENTS, envelope, strict=True)} == expected["envelope"]


@pytest.mark.parametrize(("given", "expected"), [case for case in _SCALAR_CASES if len(case.values[0]) > 1])
def test_sag_p07_the_pick_does_not_depend_on_the_order_given(given, expected):
    """SAG-P07: every order of the same points picks the same elements, for each selector — every permutation of each
    case of two to five points.

    Red before Z-29r: ``backend.app.services.signals.aggregation`` does not exist.
    """
    aggregation = _aggregation("select_point")
    points = [_observed(_day(day), raw) for day, raw in given]
    differing = {}
    for order in itertools.permutations(points):
        picked = {selector: _picked(order, aggregation.select_point(list(order), selector)) for selector in SELECTORS}
        if picked != expected:
            differing[tuple(point.date.day for point in order)] = picked
    assert not differing, f"{len(differing)} orders (days as given) pick otherwise than {expected}, e.g. {next(iter(differing.items()))}"


# =============================================================================
# SAG-E — REFUSALS
# =============================================================================


@pytest.mark.parametrize(
    "selector",
    [
        pytest.param("median", id="unknown-word"),
        pytest.param("minimum", id="ai-export-field-name"),
        pytest.param("FIRST", id="wrong-case"),
        pytest.param("", id="empty"),
        pytest.param(SignalAggregationProfile.FIRST_WITH_RANGE, id="a-profile-is-not-a-selector"),
    ],
)
def test_sag_e01_select_point_refuses_an_unknown_selector(selector):
    """SAG-E01: any selector but the four raises ValueError: an unknown word, AI Export's field name, the wrong case,
    empty, a profile in place of its selector.

    Red before Z-29r: ``backend.app.services.signals.aggregation`` does not exist.
    """
    aggregation = _aggregation("select_point")
    points = [_observed(_day(5), "1"), _observed(_day(6), "2")]
    with pytest.raises(ValueError):
        aggregation.select_point(points, selector)


@pytest.mark.parametrize("profile", NOT_SCALAR, ids=str)
def test_sag_e02_scalar_representative_refuses_a_non_scalar_profile_naming_it(profile):
    """SAG-E02: ``scalar_representative`` raises ValueError for band_envelope and events_verbatim, the message naming
    the profile (as the chart's throw does, timeSeriesAggregation.ts:352) — not a KeyError of the map.

    Red before Z-29r: ``backend.app.services.signals.aggregation`` does not exist.
    """
    aggregation = _aggregation("scalar_representative")
    points = [_observed(_day(5), "1"), _observed(_day(6), "2")]
    with pytest.raises(ValueError, match=f"(?i){re.escape(profile.value)}"):
        aggregation.scalar_representative(points, profile)


# =============================================================================
# SAG-A — AI EXPORT THROUGH THE ONE HOME, ITS OUTPUTS UNCHANGED
# =============================================================================


@dataclasses.dataclass(frozen=True, eq=False)
class _Call:
    """One call AI Export made to ``aggregation.select_point``, read through the accessors it passed."""

    points: tuple[object, ...]
    selector: object
    accessors: dict[str, Callable[[object], object]]

    def pairs(self) -> frozenset[tuple[object, object]]:
        date_of = self.accessors.get("date", _DATE)
        value_of = self.accessors.get("value", _VALUE)
        return frozenset((date_of(point), value_of(point)) for point in self.points)


def _spy_on_select_point(monkeypatch: pytest.MonkeyPatch, aggregation: ModuleType, steer: Callable[..., object] | None = None) -> list[_Call]:
    """Replace the module attribute ``select_point`` with a spy that records every call and answers the original's
    answer, or ``steer``'s when given. Only a call made through the module attribute reaches it (point 7)."""
    original = aggregation.select_point
    calls: list[_Call] = []

    def spy(points, selector, **accessors):
        given = tuple(points)
        calls.append(_Call(points=given, selector=selector, accessors=dict(accessors)))
        answer = original(given, selector, **accessors)
        return answer if steer is None else steer(given, selector, answer, accessors)

    monkeypatch.setattr(aggregation, "select_point", spy)
    return calls


def _steer(points: tuple[object, ...], selector: str, answer: object, accessors: Mapping[str, Callable[[object], object]]) -> object:
    """Another valid answer than the chart rule's, so that AI Export's statistics show whose answer they kept: the second
    point in date order for "first", the second to last for "last" (from three points), the LATEST of the tied extremes
    for "min" / "max"."""
    if answer is None:
        return None
    ordered = sorted(points, key=accessors.get("date", _DATE))
    if selector == "first":
        return ordered[1] if len(ordered) >= 3 else answer
    if selector == "last":
        return ordered[-2] if len(ordered) >= 3 else answer
    value_of = accessors.get("value", _VALUE)
    return [point for point in ordered if value_of(point) == value_of(answer)][-1]


def _assert_asked(calls: Sequence[_Call], expected: Mapping[str, frozenset[tuple[object, object]]]) -> None:
    """Each expected point set went to ``select_point`` whole, with each of the four selectors, and no call carried
    another non-empty set (two buckets mixed, part of one)."""
    assert calls, f"AI Export never called {AGGREGATION_MODULE}.select_point through the module attribute (aggregation.select_point(...)): it still picks first / minimum / maximum / last by itself"
    asked: dict[frozenset[tuple[object, object]], set[object]] = collections.defaultdict(set)
    for call in calls:
        if call.points:
            asked[call.pairs()].add(call.selector)
    unasked = {label: sorted(set(SELECTORS) - asked.get(pairs, set())) for label, pairs in expected.items()}
    unasked = {label: selectors for label, selectors in unasked.items() if selectors}
    assert not unasked, f"select_point was not asked these selectors over exactly these points: {unasked}"
    strangers = sorted(sorted(pairs) for pairs in asked if pairs not in expected.values())
    assert not strangers, f"select_point was asked over points that are no bucket's (no component's) whole: {strangers}"


#: Three buckets of January: 5-7, 8-11, 12-13.
_THREE_BUCKETS = ((5, 7), (8, 11), (12, 13))
#: A scalar series over them, given out of order: days 5-7 with tied minima, days 8-11 with tied extremes, 12-13 empty.
_SCALAR_SERIES = ((10, "4"), (7, "5"), (5, "9"), (11, "-2"), (8, "4"), (6, "5"), (9, "-2.0"))
#: A band series over them, given out of order, one row without its middle.
_BAND_SERIES = ((6, "1", "3", "6"), (9, "-3", "-1", "2"), (5, "2", "4", "8"), (8, "-4", "-2", "1"), (7, "0", None, "7"))


def test_sag_a01_ai_export_scalar_statistics_ask_select_point_for_each_bucket(monkeypatch: pytest.MonkeyPatch):
    """SAG-A01: ``aggregate_scalar_statistics`` asks ``aggregation.select_point`` for "first", "min", "max" and "last"
    over each non-empty bucket's points, whole, and over nothing else — seen by a spy that delegates to the original,
    so the outputs stay what they are. The spy replaces the module attribute: AI Export calls
    ``aggregation.select_point(...)`` (point 7).

    Red before Z-29r: the module does not exist; with it, AI Export never calls it (``_scalar_statistics_for_bucket``
    picks by itself).
    """
    aggregation = _aggregation("select_point")
    calls = _spy_on_select_point(monkeypatch, aggregation)
    plan = _plan(*_THREE_BUCKETS)
    points = [_observed(_day(day), raw) for day, raw in _SCALAR_SERIES]
    aggregate_scalar_statistics(points, plan)
    expected = {f"bucket {bucket.index}": frozenset((point.date, point.value) for point in points if bucket.contains(point.date)) for bucket in plan.buckets}
    _assert_asked(calls, {label: pairs for label, pairs in expected.items() if pairs})


def test_sag_a02_ai_export_band_statistics_ask_select_point_for_each_component(monkeypatch: pytest.MonkeyPatch):
    """SAG-A02: ``aggregate_band_statistics`` asks ``aggregation.select_point`` for the four selectors over each bucket's
    lower, middle and upper values, each component apart (a row without its middle is left out of that component only),
    whole, and over nothing else.

    Red before Z-29r: the module does not exist; with it, AI Export never calls it.
    """
    aggregation = _aggregation("select_point")
    calls = _spy_on_select_point(monkeypatch, aggregation)
    plan = _plan(*_THREE_BUCKETS)
    rows = _band_points(_BAND_SERIES)
    aggregate_band_statistics(rows, plan)
    expected = {f"bucket {bucket.index} {name}": frozenset((row.date, getattr(row, name)) for row in rows if bucket.contains(row.date) and getattr(row, name) is not None) for bucket in plan.buckets for name in BAND_COMPONENTS}
    _assert_asked(calls, {label: pairs for label, pairs in expected.items() if pairs})


def test_sag_a03_ai_export_scalar_statistics_are_select_point_answers(monkeypatch: pytest.MonkeyPatch):
    """SAG-A03: the statistics AI Export returns are the elements ``select_point`` answered, not values computed beside
    it: a spy answering otherwise — the second point for "first", the second to last for "last", the latest of the tied
    extremes, each still a valid statistic — is followed.

    Red before Z-29r: the module does not exist; with it, AI Export's statistics are the chart rule's, computed without
    it (first day 5, min day 5, max day 6, last day 9).
    """
    aggregation = _aggregation("select_point")
    calls = _spy_on_select_point(monkeypatch, aggregation, steer=_steer)
    points = [_observed(_day(day), raw) for day, raw in ((8, "9"), (5, "5"), (9, "7"), (6, "9"), (7, "5"))]
    (statistics,) = aggregate_scalar_statistics(points, _plan((5, 9)))
    assert calls, f"AI Export never called {AGGREGATION_MODULE}.select_point through the module attribute"
    assert _reads(statistics) == {"first": (6, "9"), "last": (8, "9"), "min": (7, "5"), "max": (8, "9")}


#: One bucket's band, given out of order, with tied extremes on every component.
_STEERED_BAND = ((8, "3", "6", "12"), (5, "1", "5", "9"), (9, "2", "5.5", "10"), (6, "3", "6", "12"), (7, "1", "5", "9"))


def test_sag_a04_ai_export_band_statistics_are_select_point_answers(monkeypatch: pytest.MonkeyPatch):
    """SAG-A04: each band component's statistics are the elements ``select_point`` answered over that component, as in
    SAG-A03.

    Red before Z-29r: the module does not exist; with it, AI Export's statistics are the chart rule's (lower first day 5,
    min day 5, max day 6, last day 9; the same days for middle and upper).
    """
    aggregation = _aggregation("select_point")
    calls = _spy_on_select_point(monkeypatch, aggregation, steer=_steer)
    (statistics,) = aggregate_band_statistics(_band_points(_STEERED_BAND), _plan((5, 9)))
    assert calls, f"AI Export never called {AGGREGATION_MODULE}.select_point through the module attribute"
    assert {name: _reads(getattr(statistics, name)) for name in BAND_COMPONENTS} == {
        "lower": {"first": (6, "3"), "last": (8, "3"), "min": (7, "1"), "max": (8, "3")},
        "middle": {"first": (6, "6"), "last": (8, "6"), "min": (7, "5"), "max": (8, "6")},
        "upper": {"first": (6, "12"), "last": (8, "12"), "min": (7, "9"), "max": (8, "12")},
    }


def test_sag_a05_select_scalar_representative_maps_through_scalar_profile_selectors(monkeypatch: pytest.MonkeyPatch):
    """SAG-A05: ``select_scalar_representative`` maps the profile through ``aggregation.SCALAR_PROFILE_SELECTORS`` read
    at the call: with the map permuted (first_with_range "max", last_with_range "min", min_with_range "last",
    max_with_range "first") it answers the permuted statistics.

    Red before Z-29r: the module does not exist; with it, AI Export keeps its own profile → statistic table.
    """
    aggregation = _aggregation("SCALAR_PROFILE_SELECTORS")
    permuted = {
        SignalAggregationProfile.FIRST_WITH_RANGE: "max",
        SignalAggregationProfile.LAST_WITH_RANGE: "min",
        SignalAggregationProfile.MIN_WITH_RANGE: "last",
        SignalAggregationProfile.MAX_WITH_RANGE: "first",
    }
    monkeypatch.setattr(aggregation, "SCALAR_PROFILE_SELECTORS", MappingProxyType(permuted))
    points = [_observed(_day(day), raw) for day, raw in ((5, "5"), (6, "9"), (7, "1"), (8, "4"))]
    (statistics,) = aggregate_scalar_statistics(points, _plan((5, 8)))  # first day 5, min day 7, max day 6, last day 8
    assert {profile.value: _read(select_scalar_representative(statistics, profile)) for profile in permuted} == {
        "first_with_range": (6, "9"),
        "last_with_range": (7, "1"),
        "min_with_range": (8, "4"),
        "max_with_range": (5, "5"),
    }, "select_scalar_representative does not follow aggregation.SCALAR_PROFILE_SELECTORS"


def test_sag_a06_select_band_envelope_maps_through_band_envelope_selectors(monkeypatch: pytest.MonkeyPatch):
    """SAG-A06: ``select_band_envelope`` maps each component through ``aggregation.BAND_ENVELOPE_SELECTORS`` read at the
    call: with lower "first", middle "min", upper "last" it answers those statistics (still an ordered envelope).

    Red before Z-29r: the module does not exist; with it, AI Export keeps lower = minimum, middle = last, upper = maximum
    written in ``select_band_envelope`` (days 6, 7, 6).
    """
    aggregation = _aggregation("BAND_ENVELOPE_SELECTORS")
    monkeypatch.setattr(aggregation, "BAND_ENVELOPE_SELECTORS", MappingProxyType({"lower": "first", "middle": "min", "upper": "last"}))
    (statistics,) = aggregate_band_statistics(_band_points(((5, "1", "2", "6"), (6, "0", "3", "7"), (7, "1", "4", "5"))), _plan((5, 7)))
    envelope = select_band_envelope(statistics)
    assert {name: _read(getattr(envelope, name)) for name in BAND_COMPONENTS} == {
        "lower": (5, "1"),
        "middle": (5, "2"),
        "upper": (7, "5"),
    }, "select_band_envelope does not follow aggregation.BAND_ENVELOPE_SELECTORS"


def _aggregated_as_scalar(profile: SignalAggregationProfile, plan: BucketPlan) -> bool:
    """Whether AI Export's dispatcher aggregates scalar points under ``profile``: it refuses them otherwise, with a
    TypeError (a band or events profile) or a ValueError (a profile without an arm)."""
    try:
        aggregates = aggregate_signal_buckets(profile, (_observed(plan.start, "1"),), plan)
    except (TypeError, ValueError):
        return False
    return all(isinstance(aggregate, ScalarBucketStatistics) for aggregate in aggregates)


def _represented_as_scalar(profile: SignalAggregationProfile, statistics: ScalarBucketStatistics) -> bool:
    """Whether ``select_scalar_representative`` takes ``profile`` (a ValueError otherwise)."""
    try:
        select_scalar_representative(statistics, profile)
    except ValueError:
        return False
    return True


def test_sag_a07_ai_export_takes_as_scalar_exactly_the_mapped_profiles():
    """SAG-A07: the profiles AI Export's dispatcher aggregates as scalar series, and those ``select_scalar_representative``
    takes, are exactly ``SCALAR_PROFILE_SELECTORS``' keys: a profile added to the enum and mapped in one place only shows
    here.

    Red before Z-29r: the module does not exist (with it, green: AI Export's four scalar profiles are the map's four).
    """
    mapped = set(_aggregation("SCALAR_PROFILE_SELECTORS").SCALAR_PROFILE_SELECTORS)
    plan = _plan((5, 7))
    (statistics,) = aggregate_scalar_statistics((_observed(_day(5), "1"),), plan)
    assert {profile for profile in SignalAggregationProfile if _aggregated_as_scalar(profile, plan)} == mapped
    assert {profile for profile in SignalAggregationProfile if _represented_as_scalar(profile, statistics)} == mapped


@pytest.mark.parametrize(("given", "expected"), _SCALAR_CASES)
def test_sag_a08_ai_export_scalar_outputs_equal_the_module(given, expected):
    """SAG-A08: the move changes no output. On each scalar case AI Export's first / min / max / last, and its
    representative of each scalar profile, equal ``select_point``'s and ``scalar_representative``'s answers (day and
    value as written), on the table's days.

    Red before Z-29r: the module does not exist (with it, green before and after the move: today's AI Export already
    picks as the chart on every case, and must still).
    """
    aggregation = _aggregation("select_point", "scalar_representative")
    points = [_observed(_day(day), raw) for day, raw in given]
    (statistics,) = aggregate_scalar_statistics(points, _plan((1, 31)))
    assert _reads(statistics) == {selector: _read_point(aggregation.select_point(points, selector)) for selector in SELECTORS}
    representatives = {profile.value: _read(select_scalar_representative(statistics, profile)) for profile in PROFILE_SELECTORS}
    assert representatives == {profile.value: _read_point(aggregation.scalar_representative(points, profile)) for profile in PROFILE_SELECTORS}
    assert _days(_reads(statistics)) == expected


@pytest.mark.parametrize(("rows", "expected"), _BAND_CASES)
def test_sag_a09_ai_export_band_outputs_equal_the_module(rows, expected):
    """SAG-A09: on each band case, each component's statistics in AI Export equal ``select_point``'s answers over that
    component, and ``select_band_envelope`` equals ``band_envelope`` (day and value as written), on the table's days.

    Red before Z-29r: the module does not exist (with it, green before and after the move).
    """
    aggregation = _aggregation("select_point", "band_envelope")
    components = _components(rows, _observed)
    (statistics,) = aggregate_band_statistics(_band_points(rows), _plan((1, 31)))
    for name, points in components.items():
        assert _reads(getattr(statistics, name)) == {selector: _read_point(aggregation.select_point(points, selector)) for selector in SELECTORS}, name
    envelope = select_band_envelope(statistics)
    ai_export = {name: _read(getattr(envelope, name)) for name in BAND_COMPONENTS}
    assert ai_export == {name: _read_point(selected) for name, selected in zip(BAND_COMPONENTS, aggregation.band_envelope(*components.values()), strict=True)}
    assert _days(ai_export) == expected


@pytest.mark.parametrize("rows", _BAND_BREAKS_ACROSS_DAYS)
def test_sag_a10_ai_export_and_the_module_refuse_the_same_envelopes(rows):
    """SAG-A10: the envelopes ``band_envelope`` refuses between components observed on different days are those AI
    Export refuses (``BandEnvelopeRepresentative``): both raise ValueError.

    Red before Z-29r: the module does not exist (with it, green before and after the move).
    """
    aggregation = _aggregation("band_envelope")
    (statistics,) = aggregate_band_statistics(_band_points(rows), _plan((1, 31)))
    with pytest.raises(ValueError):
        select_band_envelope(statistics)
    with pytest.raises(ValueError):
        aggregation.band_envelope(*_components(rows, _observed).values())


# =============================================================================
# SAG-T — THE TABLE IS THE CHART'S RULE (green by design)
# =============================================================================


def _ts_select_signal_representative(points, profile, value_of=_VALUE, date_of=_DATE):
    """``selectSignalRepresentative`` (timeSeriesAggregation.ts:341-353), line by line: the table's oracle, never the
    code under test's. ``Array.prototype.sort`` is stable; ``reduce`` without a seed starts from ``ordered[0]``."""
    if len(points) == 0:  # :342
        return None
    ordered = sorted(points, key=date_of)  # :343, [...points].sort by ISO date: a sorted copy
    if profile == "first_with_range":  # :344
        return ordered[0]
    if profile == "last_with_range":  # :345
        return ordered[-1]
    if profile == "min_with_range":  # :346-348
        return functools.reduce(lambda selected, point: point if value_of(point) < value_of(selected) else selected, ordered)
    if profile == "max_with_range":  # :349-351
        return functools.reduce(lambda selected, point: point if value_of(point) > value_of(selected) else selected, ordered)
    raise ValueError(f"Aggregation profile '{profile}' is not valid for a scalar signal series")  # :352


def _ts_band_representative(points, mode, value_of=_VALUE, date_of=_DATE):
    """``bandRepresentative`` (timeSeriesAggregation.ts:375-383), line by line."""
    candidates = sorted(points, key=date_of)  # :376
    if not candidates:  # :377
        raise ValueError("Cannot aggregate an empty band bucket")
    if mode == "last":  # :378
        return candidates[-1]
    if mode == "min":  # :379-382
        return functools.reduce(lambda selected, candidate: candidate if value_of(candidate) < value_of(selected) else selected, candidates)
    return functools.reduce(lambda selected, candidate: candidate if value_of(candidate) > value_of(selected) else selected, candidates)


def _ts_envelope(lower, middle, upper, value_of=_VALUE, date_of=_DATE):
    """The envelope of ``downsampleRenderedSignal`` (timeSeriesAggregation.ts:422-426): lower 'min', middle 'last',
    upper 'max', and the throw when lower > middle or middle > upper."""
    selected = (
        _ts_band_representative(lower, "min", value_of, date_of),  # :422
        _ts_band_representative(middle, "last", value_of, date_of),  # :423
        _ts_band_representative(upper, "max", value_of, date_of),  # :424
    )
    low, mid, high = (value_of(point) for point in selected)
    if low > mid or mid > high:  # :425
        raise ValueError("produced an invalid aggregated envelope")  # :426
    return selected


@pytest.mark.parametrize(("given", "expected"), _SCALAR_CASES)
def test_sag_t01_the_scalar_table_is_select_signal_representative(given, expected):
    """SAG-T01: each scalar case's expected days are those ``selectSignalRepresentative``, transcribed, picks on the
    same points as JS numbers.

    Green before Z-29r, by design: it pins the table against the TypeScript, not the code.
    """
    points = [_reading(_day(day), raw) for day, raw in given]
    assert {selector: _picked(points, _ts_select_signal_representative(points, profile)) for profile, selector in PROFILE_SELECTORS.items()} == expected


@pytest.mark.parametrize(("rows", "expected"), _BAND_CASES_CHART)
def test_sag_t02_the_band_table_is_the_chart_envelope(rows, expected):
    """SAG-T02: each band case the chart can draw expects the days its envelope, transcribed, picks.

    Green before Z-29r, by design: it pins the table against the TypeScript, not the code.
    """
    components = _components(rows, _reading)
    envelope = _ts_envelope(*components.values())
    assert {name: _picked(components[name], selected) for name, selected in zip(BAND_COMPONENTS, envelope, strict=True)} == expected


@pytest.mark.parametrize("rows", _BAND_BREAKS_IN_A_ROW)
def test_sag_t03_the_chart_throws_on_the_rows_out_of_order(rows):
    """SAG-T03: the rows out of order of the table are refused by the chart's envelope, transcribed.

    Green before Z-29r, by design: it pins the table against the TypeScript, not the code.
    """
    with pytest.raises(ValueError, match="invalid aggregated envelope"):
        _ts_envelope(*_components(rows, _reading).values())


# =============================================================================
# SAG-S — Z-29s-a: ONE SIGNAL SERIES REDUCED ONTO A SAMPLED PRICE SERIES
# =============================================================================

#: The reducer of Z-29s-a (points 9-12), read from the module at the call (``_sampler``): a name imported at the top would
#: stop the 26 tests above from collecting while it is missing.
SAMPLER = "sample_signal_series"
#: The case table both stacks read: every case through ``sample_signal_series`` here, the browser_parity ones through
#: ``downsampleRenderedSignal`` in timeSeriesAggregation.test.ts.
SAMPLING_TABLE = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "signals" / "signal_sampling_cases.v1.json").read_text(encoding="utf-8"))
SAMPLING_CASE_KEYS = {"id", "kind", "profile", "resolution", "render_dates", "points", "expected", "browser_parity", "note"}
SAMPLING_KINDS = {"line": SignalLineSeries, "area": SignalAreaSeries, "bar": SignalBarSeries, "band": SignalBandSeries}
SAMPLING_RESOLUTIONS = ("daily", "weekly", "monthly")
#: A profile that fits each kind, as the plugins declare them (a band: band_envelope; a scalar: one of the four).
FITTING_PROFILE = {"line": "last_with_range", "area": "min_with_range", "bar": "last_with_range", "band": "band_envelope"}
#: What every built output carries; only the points vary.
_OUTPUT = {
    "key": "output",
    "label_key": "signals.test.output",
    "semantic_id": "test.output",
    "semantic_description": "A test output reduced onto the dates of a sampled price series.",
    "unit": SignalUnit.NONE,
    "axis": SignalAxisSpec(key="test", role=SignalAxisRole.INDEPENDENT),
}


def _sampler() -> Callable[..., object]:
    """``aggregation.sample_signal_series``, read at the call: while it is missing each SAG-S test fails saying so."""
    sample = getattr(_aggregation(), SAMPLER, None)
    if sample is None:
        pytest.fail(f"Z-29s-a: {AGGREGATION_MODULE}.{SAMPLER} is missing — sample_signal_series(series, profile, resolution, render_dates), one signal series reduced onto a sampled price series' dates")
    return sample


def _reduce(series: object, profile: str, resolution: str, render_dates: Sequence[date]) -> object:
    """``sample_signal_series`` called as the contract writes it: the series, the profile (a ``SignalAggregationProfile``
    member), the step, the render dates."""
    return _sampler()(series, SignalAggregationProfile(profile), resolution, list(render_dates))


def _dumped(series: object) -> list[dict]:
    """A series' points as the wire writes them."""
    return [point.model_dump(mode="json") for point in series.points]


def _bucket_bounds(day: date, resolution: str) -> tuple[date, date]:
    """The first and last day of ``day``'s bucket — the day; Monday to Sunday of its ISO week; the 1st to the last day of
    its month — walked here, not read from ``price_sampling``."""
    if resolution == "weekly":
        monday = day - timedelta(days=day.isoweekday() - 1)
        return monday, monday + timedelta(days=6)
    if resolution == "monthly":
        first = day.replace(day=1)
        return first, (first + timedelta(days=31)).replace(day=1) - timedelta(days=1)
    return day, day


def _table_series(case: Mapping[str, typing.Any], field: str = "points") -> object:
    """The case's ``points`` (or ``expected``) as the series a plugin sends: the class of its kind, ``_OUTPUT``'s fields."""
    if case["kind"] == "band":
        points = [SignalBandPoint(date=date.fromisoformat(point["date"]), lower=point["lower"], middle=point["middle"], upper=point["upper"]) for point in case[field]]
    else:
        points = [SignalValuePoint(date=date.fromisoformat(point["date"]), value=point["value"]) for point in case[field]]
    return SAMPLING_KINDS[case["kind"]](**_OUTPUT, points=points)


def _render_dates_wrong(case: Mapping[str, typing.Any]) -> list[str]:
    """What breaks ``sample_dates``' shape in a case's render dates: one per bucket, the buckets one after the other (so
    ascending), each the last day of its bucket but the last one, which may be cut (the range's end); daily, consecutive
    days."""
    resolution = case["resolution"]
    days = [date.fromisoformat(day) for day in case["render_dates"]]
    if not days:
        return ["no render date"]
    buckets = [_bucket_bounds(day, resolution) for day in days]
    wrong = []
    for (day, (_start, end)), (next_start, _next_end) in zip(zip(days, buckets, strict=True), buckets[1:], strict=False):
        if day != end:
            wrong.append(f"{day} is not the last day of its {resolution} bucket")
        if next_start != end + timedelta(days=1):
            wrong.append(f"the bucket after {day}'s does not start the day after it ends")
    return wrong


def test_sag_s01_the_case_table_is_sampled_dates_and_documents_its_residues():
    """SAG-S01: the shared case table is well formed: version 1 and a description; each case with exactly its keys, a
    unique id, a kind (line, area, bar, band), a profile that fits it (a band: band_envelope; else a scalar profile), a
    step, render dates in ``sample_dates``' shape (one per bucket, the buckets one after the other, each the last day of
    its bucket but the last one, cut at the range's end; daily, consecutive days), points and expected that build valid
    series of that kind (dates strictly increasing, one value at least), and a note. At least one case is not drawn as
    the browser draws it (browser_parity false: the residues R1 and R3, and a synthetic input), each said in its note —
    the residues stay documented where both stacks read them.

    Green before Z-29s-a, by design: it pins the table, not the code.
    """
    assert (SAMPLING_TABLE.get("version"), bool(str(SAMPLING_TABLE.get("description", "")).strip())) == (1, True), {key: SAMPLING_TABLE.get(key) for key in ("version", "description")}
    cases = SAMPLING_TABLE["cases"]
    assert len({case["id"] for case in cases}) == len(cases), "two cases share an id"
    wrong: dict[str, list[str]] = {}
    for case in cases:
        found = []
        if set(case) != SAMPLING_CASE_KEYS:
            found.append(f"keys {sorted(set(case) ^ SAMPLING_CASE_KEYS)} differ")
        elif case["kind"] not in SAMPLING_KINDS or case["resolution"] not in SAMPLING_RESOLUTIONS:
            found.append(f"kind {case['kind']!r}, resolution {case['resolution']!r}")
        else:
            band = case["kind"] == "band"
            if (case["profile"] == "band_envelope") != band or case["profile"] not in {*PROFILE_SELECTORS, SignalAggregationProfile.BAND_ENVELOPE}:
                found.append(f"profile {case['profile']!r} does not fit a {case['kind']}")
            found.extend(_render_dates_wrong(case))
            for field in ("points", "expected"):
                try:
                    _table_series(case, field)
                except ValueError as invalid:
                    found.append(f"{field} build no valid {case['kind']} series: {invalid}")
            if not str(case["note"]).strip():
                found.append("no note")
        if found:
            wrong[case["id"]] = found
    assert not wrong, wrong
    residues = [case["id"] for case in cases if case["browser_parity"] is False]
    assert residues, "no case with browser_parity false: the residues R1 and R3 are no longer documented in the table"
    assert all(isinstance(case["browser_parity"], bool) for case in cases), [case["id"] for case in cases if not isinstance(case["browser_parity"], bool)]


@pytest.mark.parametrize("case", SAMPLING_TABLE["cases"], ids=lambda case: case["id"])
def test_sag_s02_every_table_case_through_sample_signal_series(case):
    """SAG-S02: each case of the shared table, built as the series a plugin sends (``SignalLineSeries``,
    ``SignalAreaSeries``, ``SignalBarSeries``, ``SignalBandSeries`` of ``SignalValuePoint`` / ``SignalBandPoint``), is
    reduced by ``sample_signal_series(series, profile, resolution, render_dates)`` into a series of the same class whose
    points, as the wire writes them, are the case's ``expected``, each gap marker included (points 9-12).

    Red at 5bbadda95: ``sample_signal_series`` does not exist.
    """
    series = _table_series(case)
    reduced = _reduce(series, case["profile"], case["resolution"], [date.fromisoformat(day) for day in case["render_dates"]])
    assert type(reduced) is type(series), f"{type(reduced).__name__} for a {type(series).__name__}"
    assert _dumped(reduced) == case["expected"], f"{case['id']}: {case['note']}"


def _scalar_points(*values: tuple[int, float | None]) -> list[SignalValuePoint]:
    """Plain points of January 2026, by (day, value)."""
    return [SignalValuePoint(date=_day(day), value=value) for day, value in values]


def _signal_band_points(*values: tuple[int, float | None, float | None, float | None]) -> list[SignalBandPoint]:
    """Band points of January 2026, by (day, lower, middle, upper)."""
    return [SignalBandPoint(date=_day(day), lower=lower, middle=middle, upper=upper) for day, lower, middle, upper in values]


def _small_series(kind: str, **fields: typing.Any) -> object:
    """A series of ``kind`` over two weeks of January 2026 (5 … 16), a null (a band: an incomplete point) among its
    points, every week with a value: ``_OUTPUT``'s fields, or ``fields``."""
    if kind == "band":
        points = _signal_band_points((5, None, None, None), (6, 1.0, 2.0, 3.0), (9, 0.5, 2.5, 3.5), (12, 1.5, 3.0, 4.0), (13, None, 3.2, None), (16, 2.0, 3.5, 4.5))
    else:
        points = _scalar_points((5, 1.0), (6, None), (7, 3.0), (9, 2.0), (12, 4.0), (16, 5.0))
    return SAMPLING_KINDS[kind](**(fields or _OUTPUT), points=points)


#: The two weeks of ``_small_series`` and the week after, by their render dates (Sundays).
_SMALL_WEEKS = (_day(11), _day(18), _day(25))


def _rich_output() -> dict[str, typing.Any]:
    """An output with every field a plugin may set, none at its default: a description, a unit, an axis with bounds, a
    view transform, a style, a reference level and a value region with a line style."""
    return {
        **_OUTPUT,
        "description_key": "signals.test.description",
        "unit": SignalUnit.PERCENTAGE,
        "axis": SignalAxisSpec(key="test_axis", role=SignalAxisRole.INDEPENDENT, minimum=-50.0, maximum=50.0),
        "view_transform": SignalViewTransform.BASE_PERCENTAGE,
        "style": SignalOutputStyle(color_role=SignalColorRole.ACCENT, line_pattern=SignalLinePattern.DASHED, width_delta=2, opacity=0.6, fill_opacity=0.35),
        "reference_levels": [SignalReferenceLevel(key="zero", label_key="signals.reference.zero", semantic="No change.", value=0.0)],
        "value_regions": [
            SignalValueRegion(
                key="high",
                label_key="signals.test.high",
                description_key="signals.test.highDescription",
                semantic="Above ten.",
                lower=10.0,
                include_upper=True,
                line_style=SignalRegionLineStyle(pattern=SignalLinePattern.DOTTED, color_role=SignalColorRole.NEGATIVE, width_delta=1, opacity=0.9),
            )
        ],
    }


@pytest.mark.parametrize("resolution", ["weekly", "monthly"])
@pytest.mark.parametrize("kind", SAMPLING_KINDS)
def test_sag_s03_the_reduced_series_keeps_every_field_but_its_points(kind, resolution):
    """SAG-S03: a line, an area, a bar and a band carrying every field a plugin may set — a description, a unit, an axis
    with bounds, a view transform, a style, a reference level, a value region with a line style — reduced weekly or
    monthly: the result is the same class and, its points aside, equal to the series as the wire writes it; its points
    are reduced (other dates than the input's).

    Red at 5bbadda95: ``sample_signal_series`` does not exist.
    """
    series = _small_series(kind, **_rich_output())
    render_dates = _SMALL_WEEKS if resolution == "weekly" else (date(2026, 1, 31),)
    reduced = _reduce(series, FITTING_PROFILE[kind], resolution, render_dates)
    assert type(reduced) is type(series), f"{type(reduced).__name__} for a {type(series).__name__}"
    assert reduced.model_dump(mode="json", exclude={"points"}) == series.model_dump(mode="json", exclude={"points"})
    assert reduced.points and {point.date for point in reduced.points} <= set(render_dates), f"not reduced onto the render dates: {_dumped(reduced)}"


def _provenance(day: int, value: float | None) -> SignalCalendarReturnProvenance:
    """A provenance of its own for the calendar-return point of January ``day``: its current price that day, so many days
    back, and the reference a week before; a point without value misses its reference."""
    current = _day(day)
    reference = current - timedelta(days=7)
    if value is None:
        return SignalCalendarReturnProvenance(status=SignalCalendarReturnPointStatus.MISSING_REFERENCE, reference_target_date=reference, current_price_date=current, current_price_days_back=day % 3)
    return SignalCalendarReturnProvenance(
        status=SignalCalendarReturnPointStatus.AVAILABLE,
        reference_target_date=reference,
        current_price_date=current,
        current_price_days_back=day % 3,
        reference_price_date=reference,
        reference_price_days_back=day % 2,
    )


def _calendar_points(*values: tuple[int, float | None]) -> list[SignalCalendarReturnValuePoint]:
    """Calendar-return points of January 2026, by (day, value), each with its own provenance."""
    return [SignalCalendarReturnValuePoint(date=_day(day), value=value, provenance=_provenance(day, value)) for day, value in values]


#: A calendar-return series over three weeks of January 2026 (the last cut on the 20th), every day of the first week,
#: with ties: the minimum of the first week on the 6th and the 8th, its maximum on the 7th and the 9th, the minimum of the
#: second week on the 12th and the 18th.
_CALENDAR_VALUES = ((5, 2.0), (6, 1.0), (7, 3.0), (8, 1.0), (9, 3.0), (10, 2.5), (11, 2.5), (12, 0.5), (14, 4.0), (18, 0.5), (19, 5.0), (20, 6.0))
_CALENDAR_RENDER = (_day(11), _day(18), _day(20))
#: The day of the point each profile's representative stands for, week by week: a tie keeps the earliest.
_CALENDAR_PICKS = {
    "first_with_range": (5, 12, 19),
    "last_with_range": (11, 18, 20),
    "min_with_range": (6, 12, 19),
    "max_with_range": (7, 14, 20),
}


@pytest.mark.parametrize("profile", _CALENDAR_PICKS)
def test_sag_s04_a_calendar_return_representative_keeps_its_provenance(profile):
    """SAG-S04: a representative is the point itself, re-dated: in a calendar-return series (``SignalCalendarReturnValuePoint``,
    each with a provenance of its own — the rolling return's) every reduced point is a calendar-return point whose value
    and provenance are those of the point the profile picks in its week, and whose date is the week's render date; for a
    tied minimum or maximum, the earliest's provenance (the 6th, not the 8th; the 7th, not the 9th; the 12th, not the
    18th). Each scalar profile, weekly, the last week cut on the 20th.

    Red at 5bbadda95: ``sample_signal_series`` does not exist.
    """
    points = _calendar_points(*_CALENDAR_VALUES)
    series = SignalLineSeries(**_OUTPUT, points=points)
    reduced = _reduce(series, profile, "weekly", _CALENDAR_RENDER)
    by_day = {point.date.day: point for point in points}
    expected = [by_day[day].model_copy(update={"date": render}).model_dump(mode="json") for day, render in zip(_CALENDAR_PICKS[profile], _CALENDAR_RENDER, strict=True)]
    assert [type(point).__name__ for point in reduced.points] == ["SignalCalendarReturnValuePoint"] * len(expected), _dumped(reduced)
    assert _dumped(reduced) == expected


def test_sag_s05_a_gap_marker_is_a_value_point_without_value():
    """SAG-S05: the marker between two runs is a ``SignalValuePoint`` without value — not a calendar-return point, which
    would need a provenance — even in a calendar-return series: runs on the 5th-6th and the 20th-21st split by a point
    without value on the 7th, last weekly (render dates the 11th, 18th and 25th) give the 6th's point re-dated on the
    11th, a marker on the 12th, the 21st's point re-dated on the 25th, each representative with its own provenance.

    Red at 5bbadda95: ``sample_signal_series`` does not exist.
    """
    points = _calendar_points((5, 1.0), (6, 2.0), (7, None), (20, 3.0), (21, 4.0))
    series = SignalLineSeries(**_OUTPUT, points=points)
    reduced = _reduce(series, "last_with_range", "weekly", (_day(11), _day(18), _day(25)))
    said = [(type(point).__name__, point.date, point.value) for point in reduced.points]
    assert said == [("SignalCalendarReturnValuePoint", _day(11), 2.0), ("SignalValuePoint", _day(12), None), ("SignalCalendarReturnValuePoint", _day(25), 4.0)], said
    assert (reduced.points[0].provenance, reduced.points[2].provenance) == (points[1].provenance, points[4].provenance)


@pytest.mark.parametrize("resolution", ["weekly", "monthly"])
@pytest.mark.parametrize(
    ("kind", "profile"),
    [
        pytest.param("line", "band_envelope", id="band-envelope-on-a-line"),
        pytest.param("area", "band_envelope", id="band-envelope-on-an-area"),
        pytest.param("bar", "band_envelope", id="band-envelope-on-a-bar"),
        pytest.param("band", "last_with_range", id="last-on-a-band"),
        pytest.param("band", "min_with_range", id="min-on-a-band"),
        pytest.param("line", "events_verbatim", id="events-verbatim-on-a-line"),
        pytest.param("band", "events_verbatim", id="events-verbatim-on-a-band"),
    ],
)
def test_sag_s06_a_profile_that_does_not_fit_the_kind_is_refused(kind, profile, resolution):
    """SAG-S06: a profile that does not fit the series' kind raises ``ValueError``, as the chart throws
    (``downsampleRenderedSignal``: a band needs band_envelope, a scalar series refuses band_envelope and
    events_verbatim): band_envelope on a line, an area or a bar; a scalar profile on a band; events_verbatim on either —
    weekly or monthly, on a series with a value in every bucket (the refusal is not an empty reduction's).

    Red at 5bbadda95: ``sample_signal_series`` does not exist.
    """
    sample = _sampler()
    render_dates = list(_SMALL_WEEKS[:2]) if resolution == "weekly" else [date(2026, 1, 31)]
    with pytest.raises(ValueError):
        sample(_small_series(kind), SignalAggregationProfile(profile), resolution, render_dates)


@pytest.mark.parametrize("kind", ["line", "band"])
def test_sag_s07_the_callers_series_is_not_changed(kind):
    """SAG-S07: ``sample_signal_series`` changes nothing of the series it is given: after a weekly reduction the series
    (a calendar-return line with a gap and every field set; a band with an incomplete point) is, as the wire writes it,
    what it was, with the same point objects in the same order, each on its own date.

    Red at 5bbadda95: ``sample_signal_series`` does not exist.
    """
    if kind == "band":
        series = _small_series("band", **_rich_output())
    else:
        series = SignalLineSeries(**_rich_output(), points=_calendar_points((5, 1.0), (6, 2.0), (7, None), (13, 3.0), (20, 4.0), (21, 0.5)))
    before = series.model_dump(mode="json")
    objects = [(id(point), point.date) for point in series.points]
    reduced = _reduce(series, FITTING_PROFILE[kind] if kind == "band" else "min_with_range", "weekly", _SMALL_WEEKS)
    assert reduced is not series, "the series given was reduced in place"
    assert series.model_dump(mode="json") == before, "the series given was changed"
    assert [(id(point), point.date) for point in series.points] == objects, "the points given were replaced, reordered or re-dated"


@pytest.mark.parametrize("kind", SAMPLING_KINDS)
def test_sag_s08_daily_gives_the_series_unchanged(kind):
    """SAG-S08: daily, a line, an area, a bar and a band are given back unchanged — as the wire writes them, their nulls
    and a band's incomplete point included, in their own class — as the chart's daily path draws the series as sent.

    Red at 5bbadda95: ``sample_signal_series`` does not exist.
    """
    series = _small_series(kind)
    reduced = _reduce(series, FITTING_PROFILE[kind], "daily", [_day(day) for day in range(5, 17)])
    assert type(reduced) is type(series), f"{type(reduced).__name__} for a {type(series).__name__}"
    assert reduced.model_dump(mode="json") == series.model_dump(mode="json")
