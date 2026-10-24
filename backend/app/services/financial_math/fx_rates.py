"""The orientation of a stored FX rate: one pair, two ways of reading it.

``fx_rates`` keeps each pair once, its two codes in alphabetical order, with the rate of the first in the second
(``fx/storage.normalize_rate_for_storage``). A conversion from ``source`` to ``destination`` reads that rate as it is
when ``source`` sorts first, and its inverse otherwise. The same rule turns a directed rate into the stored one: the
inversion is its own inverse.

And the rates a calculation reads by day, kept as steps (P3, «formule veloci»): ``AskedDayRates`` answers on the days
asked, as a map filled a day at a time did, from the days a stored rate changes.
"""

from __future__ import annotations

import bisect
from collections.abc import Iterable, Iterator, Mapping
from datetime import date, timedelta
from decimal import Decimal
from typing import Protocol


def oriented_rate[R](rate: R, source: str, destination: str) -> R:
    """The rate from ``source`` to ``destination`` of a pair whose rate is kept in alphabetical order (J-1).

    ``rate`` when ``source`` sorts before ``destination``, its inverse otherwise — in the rate's own number type
    (``Decimal``, the PAC's ``ExactRatio``): ``type(rate)(1) / rate``. Applied to a directed rate it gives the stored one,
    since the inversion is its own inverse. A zero rate has no inverse: the type's division error, never a value.
    """
    if source < destination:
        return rate
    return type(rate)(1) / rate


class UnitRateReader(Protocol):
    """A unit rate by day as steps (``fx.conversion.UnitRateSteps``): the last step on or before the day, None before
    the first."""

    days: tuple[date, ...]
    values: tuple[Decimal, ...]

    def at(self, day: date) -> Decimal | None: ...


def merged_windows(windows: Iterable[tuple[date, date]]) -> tuple[tuple[date, date], ...]:
    """Ascending windows of days (both ends included), overlapping or touching ones joined; a window that ends before it
    starts holds no day and is left out."""
    merged: list[tuple[date, date]] = []
    for first, last in sorted(window for window in windows if window[0] <= window[1]):
        if merged and first <= merged[-1][1] + timedelta(days=1):
            merged[-1] = (merged[-1][0], max(merged[-1][1], last))
        else:
            merged.append((first, last))
    return tuple(merged)


class AskedDayRates(Mapping[tuple, Decimal]):
    """Unit rates on the days asked only (P3, «formule veloci»): a map built day by day, read from steps.

    ``steps[(source, destination)]`` gives the rate of any day (the last step on or before it); here a key reads it only
    on a day inside a window asked for its pair, and only when there is a rate, as the map a day-by-day request held —
    any other day is absent, so ``get`` gives None there. Keys are ``(source, destination, day)``, or ``(source, day)``
    with ``fixed_destination``, which then reads only the pairs into that destination. Iterating walks every asked day:
    for tests and diagnostics, never on a hot path. Read-only once built: the engine's worker threads read it.
    ``step_series()`` gives each source's steps, for a reader that carries the last rate forward
    (``native_cash.NativeCash._rate_at``) and needs no day without a step.
    """

    def __init__(self, steps: Mapping[tuple[str, str], UnitRateReader], windows: Mapping[tuple[str, str], Iterable[tuple[date, date]]], *, fixed_destination: str | None = None) -> None:
        self._steps = {pair: reader for pair, reader in steps.items() if fixed_destination is None or pair[1] == fixed_destination}
        self._windows = {pair: merged_windows(asked) for pair, asked in windows.items() if fixed_destination is None or pair[1] == fixed_destination}
        self._starts = {pair: tuple(first for first, _last in asked) for pair, asked in self._windows.items()}
        self._fixed_destination = fixed_destination

    def _pair_and_day(self, key: tuple) -> tuple[tuple[str, str], date]:
        if self._fixed_destination is not None:
            source, day = key
            return (source, self._fixed_destination), day
        source, destination, day = key
        return (source, destination), day

    def _asked(self, pair: tuple[str, str], day: date) -> bool:
        index = bisect.bisect_right(self._starts.get(pair, ()), day) - 1
        return index >= 0 and day <= self._windows[pair][index][1]

    def __getitem__(self, key: tuple) -> Decimal:
        try:
            pair, day = self._pair_and_day(key)
        except (TypeError, ValueError):
            raise KeyError(key) from None
        steps = self._steps.get(pair)
        try:
            value = steps.at(day) if steps is not None and self._asked(pair, day) else None
        except TypeError:
            # A day of another type than the windows' (a datetime): absent, as in a dict keyed by dates
            raise KeyError(key) from None
        if value is None:
            raise KeyError(key)
        return value

    def __iter__(self) -> Iterator[tuple]:
        for pair, asked in self._windows.items():
            steps = self._steps.get(pair)
            if steps is None:
                continue
            for first, last in asked:
                day = first
                while day <= last:
                    if steps.at(day) is not None:
                        yield (pair[0], day) if self._fixed_destination is not None else (pair[0], pair[1], day)
                    day += timedelta(days=1)

    def __len__(self) -> int:
        return sum(1 for _key in self)

    def reading_change_days(self, source: str, destination: str | None = None) -> tuple[date, ...]:
        """The days on which this view's reading of a pair may differ from its reading the day before, ascending.

        Inside an asked window the reading is the last step on or before the day, so it moves only on a step; it appears
        on a window's first day and disappears the day after its last. Every day the reading changes is here; a day here
        need not be a change (a step equal to the one before). ``destination`` defaults to ``fixed_destination``; a pair
        without steps or windows gives none. The calendar a day-by-day reader would walk, reduced to these days.
        """
        destination = destination if destination is not None else self._fixed_destination
        pair = (source, destination)
        steps = self._steps.get(pair)
        asked = self._windows.get(pair, ())
        if steps is None or not asked or not steps.days:
            return ()
        days: set[date] = set()
        for first, last in asked:
            days.add(first)
            if last < date.max:
                days.add(last + timedelta(days=1))
            low, high = bisect.bisect_right(steps.days, first), bisect.bisect_right(steps.days, last)
            days.update(steps.days[low:high])
        return tuple(sorted(days))

    def step_series(self) -> dict[str, tuple[tuple[date, ...], tuple[Decimal, ...]]]:
        """By source, the days and values of its steps (each the rate from that day on), ascending; a source without a
        step is left out. Only with ``fixed_destination`` (one destination, so one series a source).

        The steps must be the ones ``fx.conversion.unit_rate_steps`` built on these very windows: a step on each window's
        first day (its anchor) and on each stored row inside a window, none between two windows. Then carrying the last
        step forward gives, on every day, the last rate of the asked days on or before it — what a map built day by day
        gave its reader.
        """
        if self._fixed_destination is None:
            raise ValueError("AskedDayRates.step_series needs a fixed destination: one series a source")
        return {pair[0]: (tuple(steps.days), tuple(steps.values)) for pair, steps in self._steps.items() if steps.days}
