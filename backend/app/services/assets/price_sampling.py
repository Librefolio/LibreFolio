"""A price series sampled for a compact chart (Z-29).

A card of the asset list draws a few hundred points at most: its chart (``LineChart.svelte``, compact) keeps the last
point of each ISO week or calendar month once the daily points pass 1.3 per pixel of its plot
(``chooseStaticResolution``, ``timeSeriesAggregation.ts``). ``POST /assets/prices/query`` can send that sample instead of
the whole daily fill: an item's ``max_points`` is the most points the chart's plot takes, and the step is chosen per
asset, on the asset's own fill (the page cannot know where a history starts); an item's ``resolution`` asks a step; an
item's ``sample_like`` takes the step of another item of the same request (a comparison's target, on its card's
buckets). The case table ``frontend/src/lib/components/charts/__tests__/compactDensityCases.json`` pins the step rule
to the chart's.

Pure: dates and the items' own fields only.
"""

from __future__ import annotations

import calendar
from collections.abc import Sequence
from datetime import date, timedelta
from typing import Any, Literal

SampleResolution = Literal["daily", "weekly", "monthly"]

#: Why a ``sample_like`` cannot be followed (Z-29): the key names no item, two items share a key, the item named has a
#: ``sample_like`` itself (itself included), or it covers another range.
SampleReferenceReason = Literal["unknown_key", "duplicate_key", "chained", "range_mismatch"]


def bucket_of(day: date, resolution: SampleResolution) -> tuple[date, date]:
    """The first and last day of the bucket that holds ``day``: the day itself, its ISO week (Monday to Sunday) or its
    calendar month, as ``mapDateToBucket`` draws them."""
    if resolution == "daily":
        return day, day
    if resolution == "weekly":
        monday = day - timedelta(days=day.weekday())
        return monday, monday + timedelta(days=6)
    return day.replace(day=1), day.replace(day=calendar.monthrange(day.year, day.month)[1])


def fill_counts(first: date, end: date) -> tuple[int, int, int]:
    """The days, ISO weeks and calendar months a daily fill from ``first`` to ``end`` (both included) touches."""
    days = (end - first).days + 1
    weeks = (bucket_of(end, "weekly")[0] - bucket_of(first, "weekly")[0]).days // 7 + 1
    months = (end.year - first.year) * 12 + end.month - first.month + 1
    return days, weeks, months


def choose_resolution(first: date, end: date, max_points: int) -> SampleResolution:
    """The finest step whose count over the fill fits in ``max_points``: daily, else weekly, else monthly, the floor,
    which may pass it. The chart's rule, ``max_points`` standing for its plot's width."""
    days, weeks, _months = fill_counts(first, end)
    if days <= max_points:
        return "daily"
    if weeks <= max_points:
        return "weekly"
    return "monthly"


def sample_dates(first: date, end: date, resolution: SampleResolution) -> list[date]:
    """The dates a sampled fill carries: the last day of each bucket from ``first``'s to ``end``'s, the last one cut at
    ``end`` — the points the compact chart draws. ``first`` is one of them only when it closes its bucket or is ``end``;
    the fill's first point travels apart (``sample_bounds``). Daily: every day."""
    if resolution == "daily":
        return [first + timedelta(days=offset) for offset in range((end - first).days + 1)]
    dates: list[date] = []
    bucket_start, bucket_end = bucket_of(first, resolution)
    while bucket_start <= end:
        dates.append(min(bucket_end, end))
        bucket_start = bucket_end + timedelta(days=1)
        bucket_end = bucket_of(bucket_start, resolution)[1]
    return dates


class SampleReferenceError(Exception):
    """An item's ``sample_like`` cannot be followed (Z-29): refused before any read."""

    def __init__(self, index: int, key: str | None, reason: SampleReferenceReason, message: str):
        super().__init__(message)
        self.index = index
        self.key = key
        self.reason = reason


def sample_reference_detail(error: SampleReferenceError) -> dict:
    """The ``detail`` of the 422 for a request whose ``sample_like`` cannot be followed."""
    return {"code": "sample_reference", "reason": error.reason, "item": error.index, "key": error.key, "message": str(error)}


def _span(item: Any) -> tuple[date, date]:
    """An item's ``date_range`` as two days: an absent ``end`` is the ``start``."""
    return item.date_range.start, item.date_range.end or item.date_range.start


def resolve_sample_references(items: Sequence[Any]) -> dict[int, int]:
    """By the position of each item with ``sample_like``, the position of the item it names (Z-29).

    Keys are unique in the request; the item named exists, has no ``sample_like`` of its own (one level, so no cycle)
    and covers the same ``date_range``, an absent ``end`` read as the ``start`` (``DateRangeModel``'s single day),
    before the ceiling cut. Raises ``SampleReferenceError`` at the first item that breaks a rule.
    """
    positions: dict[str, int] = {}
    for index, item in enumerate(items):
        key = getattr(item, "key", None)
        if key is None:
            continue
        if key in positions:
            raise SampleReferenceError(index, key, "duplicate_key", f"item {index}: key {key!r} is already the key of item {positions[key]}")
        positions[key] = index
    references: dict[int, int] = {}
    for index, item in enumerate(items):
        target = getattr(item, "sample_like", None)
        if target is None:
            continue
        own_key = getattr(item, "key", None)
        if target not in positions:
            raise SampleReferenceError(index, own_key, "unknown_key", f"item {index}: sample_like {target!r} names no item of the request")
        named = items[positions[target]]
        if getattr(named, "sample_like", None) is not None:
            raise SampleReferenceError(index, own_key, "chained", f"item {index}: sample_like {target!r} names an item that has a sample_like itself")
        if _span(named) != _span(item):
            raise SampleReferenceError(index, own_key, "range_mismatch", f"item {index}: sample_like {target!r} names an item with another date_range")
        references[index] = positions[target]
    return references
