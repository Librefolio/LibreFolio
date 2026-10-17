"""The Δ columns the Assets and FX pages compute today, ported to Python: the parity oracle of MF-P2.

The fixed-period changes of MF-P2 (``services/assets/period_changes.py``, ``services/fx/period_changes.py``) must give
the numbers these pages show. The functions below port the page code line for line, so that a change on either side
turns the comparison red:

- Assets: ``computePeriodDelta`` and ``computeDerivedPriceState`` of ``frontend/src/lib/utils/assetPriceDerived.ts``,
  run on the dense series of ``POST /assets/prices/query``;
- FX: the page's own ``computePeriodDelta`` in ``frontend/src/routes/(app)/fx/+page.svelte`` with ``displayFxDelta`` and
  ``displayFxRate`` of ``frontend/src/lib/stores/fxStoreRegistry.ts``, run on the per-day rates of
  ``POST /fx/currencies/convert``.

Two deliberate differences, both stated so nobody mistakes them for the page:

- The time zone. Both pages find the reference day with ``new Date(last.date); setDate(getDate() − N);
  toISOString().slice(0, 10)``: the date string parses as UTC midnight, ``setDate`` moves it in the browser's local
  time, ``toISOString`` reads it back in UTC. That is ``last − N`` calendar days only while the browser's UTC offset is
  the same on both days; when the offset of the reference day is larger, the page lands one day early (Europe/Rome:
  2025-11-15 − 30 → 2025-10-15, not 2025-10-16; America/New_York: 2025-11-05 − 7 → 2025-10-28). The ports use calendar
  arithmetic — the page as it computes in a UTC browser, and what the services do.
- Decimal instead of float. A float port would make every comparison a tolerance; the tests seed values of the form
  2^a·5^b (``seeds.py``), whose quotients terminate, so the page's ``(last − ref) / ref × 100`` and the service's
  ``(last / ref − 1) × 100`` are the same Decimal and are compared exactly.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date, timedelta
from decimal import Decimal

#: The Δ columns of both pages, in display order: ``deltas['1D']`` first, then ``DELTA_PERIODS``
#: (``assetPriceDerived.ts``: ``DELTA_PERIODS`` and ``computeDerivedPriceState``; the FX page keeps its own copy of the
#: list in ``fx/+page.svelte`` and puts ``'1D'`` first in ``fxTableRows`` the same way).
PAGE_PERIODS: tuple[tuple[str, int], ...] = (
    ("1D", 1),
    ("1W", 7),
    ("1M", 30),
    ("3M", 91),
    ("6M", 182),
    ("1Y", 365),
    ("2Y", 730),
    ("3Y", 1095),
    ("5Y", 1825),
)


def asset_page_chart(points: Iterable[tuple[date, Decimal | None]]) -> list[tuple[date, Decimal]]:
    """``chartData`` of ``computeDerivedPriceState``: each price point's date and ``Number(p.close ?? 0)``, in order."""
    return [(day, close if close is not None else Decimal(0)) for day, close in points]


def asset_page_period_delta(chart: Sequence[tuple[date, Decimal]], period_days: int) -> Decimal | None:
    """``computePeriodDelta(chartData, periodDays)`` of ``assetPriceDerived.ts``: a percentage, or None.

    The last point is the anchor; the reference is the last point dated on or before ``anchor date − period_days``
    (the scan runs backward from the end). None without points, with a zero anchor, without a reference, or with a
    zero reference: ``((last − ref) / ref) × 100`` otherwise.
    """
    if not chart:
        return None
    last_day, last_value = chart[-1]
    if last_value == 0:
        return None
    target = last_day - timedelta(days=period_days)
    reference = next((point for point in reversed(chart) if point[0] <= target), None)
    if reference is None or reference[1] == 0:
        return None
    return (last_value - reference[1]) / reference[1] * 100


def asset_page_deltas(chart: Sequence[tuple[date, Decimal]]) -> dict[str, Decimal | None]:
    """``deltas`` of ``computeDerivedPriceState``: ``'1D'``, then every ``DELTA_PERIODS`` entry."""
    return {key: asset_page_period_delta(chart, days) for key, days in PAGE_PERIODS}


def _display_fx_rate(rate: Decimal | None, inverted: bool) -> Decimal | None:
    """``displayFxRate`` of ``fxStoreRegistry.ts``: None for a missing or non-positive rate, ``1 / rate`` when inverted."""
    if rate is None or rate <= 0:
        return None
    return 1 / rate if inverted else rate


def fx_page_period_delta(data: Sequence[tuple[date, Decimal | None]], period_days: int, inverted: bool) -> Decimal | None:
    """``computePeriodDelta(data, periodDays, inverted)`` of ``fx/+page.svelte``: a percentage, or None.

    ``data`` is the pair's ``FxDataPoint`` list: one point per day ``POST /fx/currencies/convert`` answered, its ``rate``
    the conversion of 1 base into the quote. Two points at least; the reference is the last point on or before
    ``last date − period_days``; the change is ``displayFxDelta(ref.rate, last.rate, inverted).pct``, with the pair read
    the other way round (``1 / rate``) when ``inverted``.
    """
    if len(data) < 2:
        return None
    last_day, last_rate = data[-1]
    target = last_day - timedelta(days=period_days)
    reference = next((point for point in reversed(data) if point[0] <= target), None)
    if reference is None:
        return None
    first = _display_fx_rate(reference[1], inverted)
    last = _display_fx_rate(last_rate, inverted)
    if first is None or last is None:
        return None
    return (last - first) / first * 100


def fx_page_deltas(data: Sequence[tuple[date, Decimal | None]], inverted: bool) -> dict[str, Decimal | None]:
    """``deltas`` of one ``fxTableRows`` entry: ``'1D'``, then every period, in the orientation the user shows."""
    return {key: fx_page_period_delta(data, days, inverted) for key, days in PAGE_PERIODS}
