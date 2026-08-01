"""Helpers ensuring calculation data never leaks outside the requested period.

Some calculations (EMA, rolling stats, ...) need history before the requested
``start`` date to "warm up" before their values are trustworthy. This module
provides the seam for fetching that extra history and, critically, for
guaranteeing it is stripped before anything is exported — both before
``start`` (warm-up-only data) and after ``end`` (accidental over-fetch).
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date as Date

from backend.app.services.ai_export.temporal.points import Dated


def warmup_window_start(start: Date, lookback_days: int) -> Date:
    """Return the earliest date raw source data should be fetched from.

    ``lookback_days`` extra days are fetched strictly so that calculations
    needing prior history can warm up; those extra days must never appear in
    the emitted output (see :func:`slice_to_requested_period`). The result is
    clamped at ``date.min`` instead of underflowing/raising when ``start`` is
    close to the minimum representable date.
    """

    if type(start) is not Date:
        raise TypeError("start must be a datetime.date instance")
    if isinstance(lookback_days, bool) or not isinstance(lookback_days, int) or lookback_days < 0:
        raise ValueError("lookback_days must be a non-negative integer")

    min_ordinal = Date.min.toordinal()
    candidate_ordinal = start.toordinal() - lookback_days
    if candidate_ordinal < min_ordinal:
        return Date.min
    return Date.fromordinal(candidate_ordinal)


def _require_valid_range(start: Date, end: Date) -> None:
    if type(start) is not Date or type(end) is not Date:
        raise TypeError("start and end must be datetime.date instances")
    if start > end:
        raise ValueError("start must not be after end")


def slice_to_requested_period[T: Dated](observations: Iterable[T], start: Date, end: Date) -> tuple[T, ...]:
    """Keep only observations within the inclusive ``[start, end]`` requested period.

    ``observations`` items must expose a ``date`` attribute (``ObservedPoint``,
    ``ContinuousMultiOutputPoint``, ``MonetaryFlowEvent``, ``DiscreteEvent``,
    ...). This drops both warm-up-only data before ``start`` and any
    accidental over-fetch after ``end`` — it is the only sanctioned way
    calculation data computed using warm-up history should reach an
    exported/aggregated result.
    """

    _require_valid_range(start, end)
    return tuple(observation for observation in observations if start <= observation.date <= end)


def assert_within_requested_period[T: Dated](observations: Iterable[T], start: Date, end: Date) -> None:
    """Raise ``ValueError`` if any observation falls outside ``[start, end]`` (defence in depth)."""

    _require_valid_range(start, end)
    leaked = sorted(observation.date for observation in observations if not (start <= observation.date <= end))
    if leaked:
        raise ValueError(f"{len(leaked)} observation(s) outside requested period [{start}, {end}] were not sliced: {leaked[:5]}")
