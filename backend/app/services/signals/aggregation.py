"""The per-bucket selection rule of the signals' ``aggregation_profile`` (Z-29r): which observation stands for a bucket.

A plugin declares, for each of its outputs, how a chart or a summary reduces its points to one per bucket (the profile,
``schemas/signals.py`` ``SignalAggregationProfile``). This module is the backend's one home of that rule: AI Export's
temporal aggregators go through it, and so does the reduction of a sampled price query item's signals for a compact chart
(``sample_signal_series``, Z-29s; ``align_signal_series``, O1). The chart keeps the same rule in the browser (``timeSeriesAggregation.ts``:
``selectSignalRepresentative``, ``bandRepresentative``, ``downsampleRenderedSignal``), tied to this one by the shared
fixtures ``aggregation_profiles.v1.json`` and ``signal_sampling_cases.v1.json`` and by ``test_signal_aggregation.py``.

Pure: no database, no clock.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from datetime import date as date_type
from datetime import timedelta
from operator import attrgetter, itemgetter
from types import MappingProxyType
from typing import Any, Literal

from backend.app.schemas.signals import SignalAggregationProfile, SignalBandPoint, SignalBandSeries, SignalBarSeries, SignalValuePoint
from backend.app.services.assets.price_sampling import SampleResolution, bucket_of

Selector = Literal["first", "last", "min", "max"]

#: The point a scalar profile keeps for a bucket. ``band_envelope`` and ``events_verbatim`` are no scalar profiles.
SCALAR_PROFILE_SELECTORS: Mapping[SignalAggregationProfile, Selector] = MappingProxyType(
    {
        SignalAggregationProfile.FIRST_WITH_RANGE: "first",
        SignalAggregationProfile.LAST_WITH_RANGE: "last",
        SignalAggregationProfile.MIN_WITH_RANGE: "min",
        SignalAggregationProfile.MAX_WITH_RANGE: "max",
    }
)

#: The point each component of a band keeps for a bucket: the envelope's widest lower and upper, and the last middle.
BAND_ENVELOPE_SELECTORS: Mapping[str, Selector] = MappingProxyType({"lower": "min", "middle": "last", "upper": "max"})

_SELECTORS: frozenset[str] = frozenset({"first", "last", "min", "max"})


def select_point[T](points: Iterable[T], selector: Selector, *, value: Callable[[T], Any] = attrgetter("value"), date: Callable[[T], Any] = attrgetter("date")) -> T | None:
    """The element of ``points`` that ``selector`` keeps, itself, or None when there is none.

    The points are taken in date order whatever the order given (a stable sort: equal dates keep it), and the caller's
    sequence is not reordered. ``"first"`` and ``"last"``: the earliest and the latest; ``"min"`` and ``"max"``: the
    smallest and the largest value, the earliest among equal values (``Decimal("2.5")`` equals ``Decimal("2.50")``).
    ``value`` and ``date`` read any element: a point with ``.value`` and ``.date``, a tuple through ``itemgetter``.
    """
    if selector not in _SELECTORS:
        raise ValueError(f"unknown selector {selector!r}: first, last, min or max")
    ordered = sorted(points, key=date)
    if not ordered:
        return None
    if selector == "first":
        return ordered[0]
    if selector == "last":
        return ordered[-1]
    chosen = ordered[0]
    for point in ordered[1:]:
        if (value(point) < value(chosen)) if selector == "min" else (value(point) > value(chosen)):
            chosen = point
    return chosen


def scalar_representative[T](points: Iterable[T], profile: SignalAggregationProfile, **accessors: Callable[[T], Any]) -> T | None:
    """The element a scalar ``profile`` keeps for a bucket (``SCALAR_PROFILE_SELECTORS``); ``band_envelope`` and
    ``events_verbatim`` raise ``ValueError``."""
    selector = SCALAR_PROFILE_SELECTORS.get(profile)
    if selector is None:
        raise ValueError(f"{getattr(profile, 'value', profile)} is not a scalar aggregation profile")
    return select_point(points, selector, **accessors)


def band_envelope[T](lower_points: Iterable[T], middle_points: Iterable[T], upper_points: Iterable[T], **accessors: Callable[[T], Any]) -> tuple[T | None, T | None, T | None]:
    """The (lower, middle, upper) elements a band keeps for a bucket (``BAND_ENVELOPE_SELECTORS``), None for an empty
    component. ``ValueError`` when the present ones break lower <= middle <= upper."""
    value = accessors.get("value", attrgetter("value"))
    chosen = (
        select_point(lower_points, BAND_ENVELOPE_SELECTORS["lower"], **accessors),
        select_point(middle_points, BAND_ENVELOPE_SELECTORS["middle"], **accessors),
        select_point(upper_points, BAND_ENVELOPE_SELECTORS["upper"], **accessors),
    )
    present = [value(point) for point in chosen if point is not None]
    if any(current > following for current, following in zip(present, present[1:], strict=False)):
        raise ValueError("a band envelope must satisfy lower <= middle <= upper")
    return chosen


def _bucketed[P](points: Iterable[P], render_date: Callable[[date_type], date_type | None]) -> dict[date_type, list[P]]:
    """``points`` by the price date of their bucket, oldest first; a point whose bucket has none is left out (Z-29s)."""
    buckets: dict[date_type, list[P]] = {}
    for point in points:
        day = render_date(point.date)
        if day is not None:
            buckets.setdefault(day, []).append(point)
    return dict(sorted(buckets.items()))


def _band_points(series: SignalBandSeries, render_date: Callable[[date_type], date_type | None]) -> list[SignalBandPoint]:
    """A band's complete points, one per bucket: the lowest lower, the last middle and the highest upper (Z-29s)."""
    complete = [point for point in series.points if point.lower is not None and point.middle is not None and point.upper is not None]
    envelope = []
    for day, members in _bucketed(complete, render_date).items():
        lower, middle, upper = band_envelope(
            [(point.date, point.lower) for point in members],
            [(point.date, point.middle) for point in members],
            [(point.date, point.upper) for point in members],
            value=itemgetter(1),
            date=itemgetter(0),
        )
        envelope.append(SignalBandPoint(date=day, lower=lower[1], middle=middle[1], upper=upper[1]))
    return envelope


def _value_runs[P](points: Iterable[P], split: bool) -> list[list[P]]:
    """The stretches of points with a value, oldest first: with ``split``, a point without a value after a value ends
    one; leading and trailing points without a value belong to none (Z-29s)."""
    runs: list[list[P]] = [[]]
    for point in points:
        if point.value is not None:
            runs[-1].append(point)
        elif split and runs[-1]:
            runs.append([])
    return [run for run in runs if run]


def _scalar_points(series: Any, selector: Selector, render_date: Callable[[date_type], date_type | None]) -> list[Any]:
    """A line's or an area's points reduced a run at a time, a bar's whole (Z-29s, ``sample_signal_series``)."""
    points: list[Any] = []
    previous_last: date_type | None = None
    for run in _value_runs(series.points, split=not isinstance(series, SignalBarSeries)):
        kept = [select_point(members, selector).model_copy(update={"date": day}) for day, members in _bucketed(run, render_date).items()]
        if not kept:
            continue
        if previous_last is not None:
            gap = previous_last + timedelta(days=1)
            if gap < kept[0].date:
                points.append(SignalValuePoint(date=gap))
            elif previous_last == kept[0].date:
                points.pop()
        points.extend(kept)
        previous_last = kept[-1].date
    return points


def sample_signal_series[S](series: S, profile: SignalAggregationProfile, resolution: SampleResolution, render_dates: Sequence[date_type]) -> S:
    """``series`` as a compact chart draws it beside prices sampled weekly or monthly (Z-29s): one point per bucket of
    ``resolution``, the one the output's ``profile`` keeps, dated as its bucket's price point (``render_dates``: the
    sampled price dates, ascending, one per bucket). The browser's rule (``downsampleRenderedSignal``, after the
    renderer's split of a line into runs, ``backendRenderer.ts``), so a card draws the reduced series as it drew the daily
    one.

    - ``"daily"``: ``series`` itself.
    - A line or an area: each run between the points sent without a value reduced alone; each point kept is the element
      itself (``select_point``) dated at its bucket's price date, so a calendar return keeps its provenance. Between two
      runs, a point without a value on the day after the first one's last point, when that day comes before the next
      run's first point; where two runs meet in one bucket, the later run's point and no gap (the browser draws both
      there: one point instead of two, accepted on 19/10).
    - A bar: its points with a value, one per bucket, no run (the browser draws a bar output whole).
    - A band (``band_envelope``): its complete points, the lowest lower, the last middle and the highest upper of each
      bucket.

    A point whose bucket has no price date is left out; a reduction that keeps no value gives ``series`` itself (a series
    holds one value at least). ``ValueError`` when ``profile`` does not fit the series' kind. ``series`` is not changed.
    """
    if resolution == "daily":
        return series
    render_by_bucket = {bucket_of(day, resolution): day for day in render_dates}

    def render_date(day: date_type) -> date_type | None:
        return render_by_bucket.get(bucket_of(day, resolution))

    if isinstance(series, SignalBandSeries):
        if profile != SignalAggregationProfile.BAND_ENVELOPE:
            raise ValueError(f"a band series takes band_envelope, not {getattr(profile, 'value', profile)}")
        points: list[Any] = _band_points(series, render_date)
    else:
        selector = SCALAR_PROFILE_SELECTORS.get(profile)
        if selector is None:
            raise ValueError(f"{getattr(profile, 'value', profile)} is not a scalar aggregation profile")
        points = _scalar_points(series, selector, render_date)
    return series.model_copy(update={"points": points}) if points else series


def align_signal_series[S](series: Sequence[S]) -> list[S]:
    """The series of ONE signal, each reduced alone by ``sample_signal_series``, on identical dates (O1, the developer's
    decision of 21/10), as ``SignalResult`` wants them (``_validate_series_alignment``).

    Reduced alone, they leave different dates: a warm-up that ends inside the range, a gap one has and another has not.
    Each gets the union of the dates the reductions left: its own points, and, where it has none, a point without a value
    (``SignalValuePoint(date=d)``; a band's: lower, middle and upper null) instead of a missing date. The browser draws
    a line's or a bar's leading and trailing points without a value as nothing, a band's from its complete points only;
    in the middle of a series such a point ends a run, which a gap marker of another series causes (residue R5).

    Series that agree are given back as they are; the others are copies in their own class with every field but ``points``
    unchanged. The list is in the order given, and neither it nor its series are changed.
    """
    dates = sorted({point.date for item in series for point in item.points})
    aligned = []
    for item in series:
        if [point.date for point in item.points] == dates:
            aligned.append(item)
            continue
        by_date = {point.date: point for point in item.points}
        empty = SignalBandPoint if isinstance(item, SignalBandSeries) else SignalValuePoint
        aligned.append(item.model_copy(update={"points": [by_date[day] if day in by_date else empty(date=day) for day in dates]}))
    return aligned
