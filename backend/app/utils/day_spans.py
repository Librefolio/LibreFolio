"""Day spans: ``(first, last)`` pairs of dates, both included.

Neutral on purpose (``utils``, no import from the services): the orientation of an FX rate (``financial_math/fx_rates.py``),
the data-quality ranges and the BRIM coverage all join spans, and the first of them may import nothing from the services.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date


def merged_spans(spans: Iterable[tuple[date, date]], *, skip_reversed: bool = False) -> list[tuple[date, date]]:
    """``(first, last)`` day spans, both included, with the overlapping and the consecutive ones merged, in order.

    The one place that joins day spans (data-quality ranges, asked FX windows, BRIM coverage): ``[(1 Mar, 3 Mar),
    (4 Mar, 4 Mar), (9 Mar, 9 Mar)]`` gives ``[(1 Mar, 4 Mar), (9 Mar, 9 Mar)]``. A span with ``last < first`` holds no
    day: it raises ValueError, or with ``skip_reversed`` it is left out.
    """
    merged: list[tuple[date, date]] = []
    for first, last in sorted(span for span in spans if not (skip_reversed and span[1] < span[0])):
        if last < first:
            raise ValueError(f"span {first}..{last} ends before it starts")
        if merged and (first - merged[-1][1]).days <= 1:
            if last > merged[-1][1]:
                merged[-1] = (merged[-1][0], last)
            continue
        merged.append((first, last))
    return merged
