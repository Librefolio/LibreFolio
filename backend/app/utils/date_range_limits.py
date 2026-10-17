"""How far back a per-day walk may go (lot X-R55, night decision N75), and how big a bulk request may be (Z-25, N77).

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

#: How many items one bulk request of prices (``POST /assets/prices/query``) or rates (``POST /fx/currencies/convert``)
#: may hold (Z-25). The web app sends a whole list page in one request, one item per asset or pair.
MAX_BULK_ITEMS = 1_000
#: How many per-day points or conversions one bulk request may build, all its items together (Z-25). The asset list on
#: "All" (from 2000) of 300 assets builds about 2.9 million; a thousand rates over 100 years would build 36.5 million.
MAX_BULK_ITEM_DAYS = 5_000_000


class BulkTooManyDaysError(Exception):
    """A bulk request would build more than ``max_item_days`` per-day points: refused before any of them is built."""

    def __init__(self, item_days: int, max_item_days: int):
        super().__init__(f"the request would build {item_days} per-day points, more than {max_item_days}")
        self.item_days = item_days
        self.max_item_days = max_item_days


def bulk_too_many_items_detail(items: int, max_items: int) -> dict:
    """The ``detail`` of the 422 for a bulk request with more than ``max_items`` items."""
    return {"code": "bulk_too_many_items", "message": f"A bulk request may hold at most {max_items} items, not {items}", "max_items": max_items, "items": items}


def bulk_too_many_days_detail(item_days: int, max_item_days: int) -> dict:
    """The ``detail`` of the 422 for a bulk request that would build more than ``max_item_days`` per-day points."""
    return {
        "code": "bulk_too_many_days",
        "message": f"A bulk request may build at most {max_item_days} per-day points, and this one would build {item_days}",
        "max_item_days": max_item_days,
        "item_days": item_days,
    }


def range_span_floor(end: date) -> date:
    """The first day a per-day walk ending at ``end`` may visit: ``RANGE_SPAN_LIMIT_DAYS`` before it, at most ``date.min``."""
    if (end - date.min).days <= RANGE_SPAN_LIMIT_DAYS:
        return date.min
    return end - timedelta(days=RANGE_SPAN_LIMIT_DAYS)
