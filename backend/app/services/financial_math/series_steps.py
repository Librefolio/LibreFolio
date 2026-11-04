"""Series as steps: one point per stretch of days during which nothing changes (D-P4, cure B).

A point holds from its ``date`` to its ``through`` (both included). The points of a series — of one key, for a series
per lot, broker or position — are in order, never overlap and lie inside the response's ``range``; a day no point covers
has no value. The report, the lots and the positions series build their steps here, and every backend reader (the AI
Export, the risk) reads them here: one home for «the value of a day» and «the steps of a list of changes».

Pure: no I/O. A point is anything with ``date`` and ``through``: an object with those attributes (a dataclass, a
pydantic model, :class:`StepRow`) or a mapping with those keys.
"""

from __future__ import annotations

import bisect
import dataclasses
from collections.abc import Callable, Hashable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any


@dataclass(frozen=True, slots=True)
class StepRow[R]:
    """A step built by :func:`steps_from_rows`: the row it holds (the first of a run of identical rows), its days and its
    key (None for a single series)."""

    row: R
    date: date
    through: date
    key: Hashable


def _date_of(point: Any) -> date:
    return point["date"] if isinstance(point, Mapping) else point.date


def _through_of(point: Any) -> date:
    return point["through"] if isinstance(point, Mapping) else point.through


def value_at[P](points: Sequence[P], day: date) -> P | None:
    """The point holding ``day`` (``date <= day <= through``), itself; None before the first, after the last or in a gap.

    A binary search on ``date``: the points must be in order and never overlap. The point is returned, not a dated
    value: which day the caller reads it for stays with the caller.
    """
    index = bisect.bisect_right(points, day, key=_date_of) - 1
    if index < 0:
        return None
    point = points[index]
    return point if day <= _through_of(point) else None


def _clipped[P](point: P, start: date, through: date) -> P:
    """``point`` with its days set to ``start``..``through``: the same object when they do not change, else a copy."""
    if _date_of(point) == start and _through_of(point) == through:
        return point
    if isinstance(point, Mapping):
        copy = dict(point)
        copy["date"], copy["through"] = start, through
        return copy  # type: ignore[return-value]
    if dataclasses.is_dataclass(point) and not isinstance(point, type):
        return dataclasses.replace(point, date=start, through=through)  # type: ignore[type-var]
    model_copy = getattr(point, "model_copy", None)
    if model_copy is not None:
        return model_copy(update={"date": start, "through": through})
    raise TypeError(f"cannot clip a {type(point).__name__}: not a mapping, a dataclass or a pydantic model")


def points_between[P](points: Sequence[P], start: date, end: date) -> list[P]:
    """The points touching ``[start, end]``, clipped to it (``date`` = max(date, start), ``through`` = min(through, end)).

    A point inside the window comes back as is; a clipped one is a copy with only its days changed. A window touching
    no point gives an empty list (for the AI Export, an empty bucket), and so does ``start > end``.
    """
    if start > end or not points:
        return []
    first = max(bisect.bisect_right(points, start, key=_date_of) - 1, 0)
    out: list[P] = []
    for index in range(first, len(points)):
        point = points[index]
        point_date = _date_of(point)
        if point_date > end:
            break
        point_through = _through_of(point)
        if point_through < start:
            continue
        out.append(_clipped(point, max(point_date, start), min(point_through, end)))
    return out


def _exact(value: Any) -> Any:
    """``value`` with every Decimal as its digits and exponent (recursively in tuples, lists and dicts): two values are
    equal only when their Decimals are the same Decimals — ``Decimal("1.10")`` is not ``Decimal("1.1")``."""
    if isinstance(value, Decimal):
        return ("__decimal__", value.as_tuple())
    if isinstance(value, (tuple, list)):
        return (type(value).__name__, tuple(_exact(item) for item in value))
    if isinstance(value, Mapping):
        return ("__mapping__", frozenset((key, _exact(item)) for key, item in value.items()))
    return value


def _runs[R](ordered: Sequence[R], days: Sequence[date], last_day: date, values: Callable[[R], Any], is_gap: Callable[[R], bool] | None) -> list[tuple[R | None, date]]:
    """One key's runs up to ``last_day``: ``(first row, first day)`` of each run of identical rows, ``(None, day)`` for a gap."""
    runs: list[tuple[R | None, date]] = []
    previous_value: Any = None
    for row, row_day in zip(ordered, days, strict=True):
        if row_day > last_day:
            break
        if is_gap is not None and is_gap(row):
            if not runs or runs[-1][0] is not None:
                runs.append((None, row_day))
            continue
        value = _exact(values(row))
        if runs and runs[-1][0] is not None and value == previous_value:
            continue
        runs.append((row, row_day))
        previous_value = value
    return runs


def steps_from_rows[R](
    rows: Iterable[R],
    *,
    day: Callable[[R], date],
    values: Callable[[R], Any],
    range_start: date,
    range_end: date,
    key: Callable[[R], Hashable] | None = None,
    is_gap: Callable[[R], bool] | None = None,
    ends: Mapping[Hashable, date] | None = None,
) -> list[StepRow[R]]:
    """The steps of the rows of the days a series may change, clipped to ``range_start``..``range_end``.

    For each key (``key(row)``, one series when None), in day order: consecutive rows whose ``values(row)`` are equal —
    Decimals compared with their exponent — make one step, which keeps the first of them. A step holds until the day
    before the key's next step; the last one until ``ends[key]`` when given (the key's last day), else ``range_end``. A
    row for which ``is_gap(row)`` is true ends the step before it and opens a gap. A step holding ``range_start`` starts
    there; steps outside the range are dropped. Keys come out in the order of their first row, each one's steps in order.

    Raises ValueError on a key with two rows on one day, or when ``range_start > range_end``.
    """
    if range_start > range_end:
        raise ValueError(f"range_start ({range_start}) is after range_end ({range_end})")
    by_key: dict[Hashable, list[R]] = {}
    for row in rows:
        by_key.setdefault(key(row) if key is not None else None, []).append(row)
    steps: list[StepRow[R]] = []
    for series_key, series_rows in by_key.items():
        ordered = sorted(series_rows, key=day)
        days = [day(row) for row in ordered]
        for previous, current in zip(days, days[1:], strict=False):
            if previous == current:
                raise ValueError(f"key {series_key!r} has two rows on {current}")
        last_day = min(ends[series_key], range_end) if ends is not None and series_key in ends else range_end
        runs = _runs(ordered, days, last_day, values, is_gap)
        for index, (run_row, run_day) in enumerate(runs):
            if run_row is None:
                continue
            through = runs[index + 1][1] - timedelta(days=1) if index + 1 < len(runs) else last_day
            if through < range_start or run_day > range_end:
                continue
            steps.append(StepRow(row=run_row, date=max(run_day, range_start), through=min(through, range_end), key=series_key))
    return steps


def merged_spans(spans: Iterable[tuple[date, date]]) -> list[tuple[date, date]]:
    """``(first, last)`` day spans, both included, with the overlapping and the consecutive ones merged, in order.

    The data-quality report's ranges (D-P4): ``[(1 Mar, 3 Mar), (4 Mar, 4 Mar), (9 Mar, 9 Mar)]`` gives
    ``[(1 Mar, 4 Mar), (9 Mar, 9 Mar)]``. A span with ``last < first`` raises ValueError.
    """
    merged: list[tuple[date, date]] = []
    for first, last in sorted(spans):
        if last < first:
            raise ValueError(f"span {first}..{last} ends before it starts")
        if merged and (first - merged[-1][1]).days <= 1:
            if last > merged[-1][1]:
                merged[-1] = (merged[-1][0], last)
            continue
        merged.append((first, last))
    return merged
