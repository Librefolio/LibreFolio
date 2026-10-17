"""Ceilings for the date ranges a request may ask (lot X-R55, night decision N75).

A range that reaches far into the future, or spans many centuries, would make the per-day loops of the price and FX
queries build millions of points. Every request range is cut at ``latest_range_end()``, tomorrow in UTC: no market
price or rate is dated later (a value stored by hand with a later date is not returned), and the extra day covers a
user whose calendar is ahead of UTC. A per-day walk with no data of its own to stop at goes back at most
``RANGE_SPAN_LIMIT_DAYS`` from its end (``range_span_floor``).

``latest_range_end()`` stands in for ``datetime_utils.latest_range_end()`` (lot R13-SEC7-1, workstream J) until that
lot enters; they compute the same day.
"""

from datetime import date, timedelta

from backend.app.utils.datetime_utils import today_date

#: How far back a per-day walk may go from the end of its range: 100 years.
RANGE_SPAN_LIMIT_DAYS = 36_525


def latest_range_end() -> date:
    """The last day a request range may reach: tomorrow in UTC."""
    return today_date() + timedelta(days=1)


def range_span_floor(end: date) -> date:
    """The first day a per-day walk ending at ``end`` may visit: ``RANGE_SPAN_LIMIT_DAYS`` before it, at most ``date.min``."""
    if (end - date.min).days <= RANGE_SPAN_LIMIT_DAYS:
        return date.min
    return end - timedelta(days=RANGE_SPAN_LIMIT_DAYS)
