"""The per-bucket selection rule of the signals' ``aggregation_profile`` (Z-29r): which observation stands for a bucket.

A plugin declares, for each of its outputs, how a chart or a summary reduces its points to one per bucket (the profile,
``schemas/signals.py`` ``SignalAggregationProfile``). This module is the backend's one home of that rule: AI Export's
temporal aggregators go through it. The chart keeps the same rule in the browser (``timeSeriesAggregation.ts``:
``selectSignalRepresentative``, ``bandRepresentative``), tied to this one by the shared fixture
``aggregation_profiles.v1.json`` and by ``test_signal_aggregation.py``.

Pure: no database, no clock.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from operator import attrgetter
from types import MappingProxyType
from typing import Any, Literal

from backend.app.schemas.signals import SignalAggregationProfile

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
