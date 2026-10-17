"""How far back a per-day walk may go (lot X-R55, night decision N75).

A range that reaches far into the future, or spans many centuries, would make the per-day loops of the price and FX
queries build millions of points. The end of every request range is cut at ``datetime_utils.latest_range_end()``,
tomorrow by the server's calendar (the one helper, shared with R13-SEC7-1): no market price or rate is dated later (a
value stored by hand with a later date is not returned), and the extra day covers a user whose today is already the
server's tomorrow. A per-day walk with no data of its own to stop at goes back at most ``RANGE_SPAN_LIMIT_DAYS`` from
its end (``range_span_floor``).
"""

from datetime import date, timedelta

#: How far back a per-day walk may go from the end of its range: 100 years.
RANGE_SPAN_LIMIT_DAYS = 36_525


def range_span_floor(end: date) -> date:
    """The first day a per-day walk ending at ``end`` may visit: ``RANGE_SPAN_LIMIT_DAYS`` before it, at most ``date.min``."""
    if (end - date.min).days <= RANGE_SPAN_LIMIT_DAYS:
        return date.min
    return end - timedelta(days=RANGE_SPAN_LIMIT_DAYS)
