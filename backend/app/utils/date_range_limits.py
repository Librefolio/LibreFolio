"""How far back a per-day walk may go (lot X-R55, night decision N75), and how big a bulk request may be (Z-25, N77).

A range that reaches far into the future, or spans many centuries, would make the per-day loops of the price and FX
queries build millions of points. The end of every request range is cut at ``datetime_utils.latest_range_end()``,
tomorrow by the server's calendar (the one helper, shared with R13-SEC7-1): no market price or rate is dated later (a
value stored by hand with a later date is not returned), and the extra day covers a user whose today is already the
server's tomorrow. A per-day walk with no data of its own to stop at goes back at most ``RANGE_SPAN_LIMIT_DAYS`` from
its end (``range_span_floor``).

A stored price or rate carries a date inside ``stored_date_bounds()`` (X-R65, night decision N83): a manual write with
a date outside is refused, a provider's point outside is skipped. A price at 0001-01-01 made a backward fill or a risk
replay walk about 740,000 days (J's SEC8-1b).
"""

from datetime import date, timedelta

from backend.app.utils.datetime_utils import EARLIEST_RANGE_START, latest_range_end

#: How far back a per-day walk may go from the end of its range: 100 years.
RANGE_SPAN_LIMIT_DAYS = 36_525

#: How many items one bulk request of prices (``POST /assets/prices/query``) or rates (``POST /fx/currencies/convert``)
#: may hold (Z-25). The web app sends a whole list page in one request, one item per asset or pair.
MAX_BULK_ITEMS = 1_000
#: How many per-day points or conversions one bulk request may build, all its items together (Z-25). Lowered from 5
#: million by R13-SEC9-2: a point costs about 25.5 µs to fill, about as much to serialize, and about 1.9 KB, so a million
#: is still close to a minute of the event loop and a few GB. The web app splits its lists into batches under it (Z-27,
#: `frontend/src/lib/api/bulkBatches.ts`); the in-process callers (risk, AI Export) share it: about 100 assets over
#: "All" (from 2000, nearly 9,800 days each), about 550 over five years.
MAX_BULK_ITEM_DAYS = 1_000_000
#: How many items one bulk write of rates or prices may hold (MF-SEC9a, from E's review of R13-SEC9): the rates of
#: ``POST /fx/currencies/rate``, the deletions of ``DELETE /fx/currencies/rate``, and the date ranges of
#: ``DELETE /assets/prices``, all assets together. Higher than ``MAX_BULK_ITEMS``: the FX page saves a CSV import in one
#: request, and daily rates since 1999 are about 7 000 rows. The statements behind them run in chunks
#: (``utils/sql_chunks``), so the cap bounds the request, not SQLite.
MAX_BULK_WRITE_ITEMS = 10_000


class BulkTooManyDaysError(Exception):
    """A bulk request would build more than ``max_item_days`` per-day points: refused before any of them is built."""

    def __init__(self, item_days: int, max_item_days: int):
        super().__init__(f"the request would build {item_days} per-day points, more than {max_item_days}")
        self.item_days = item_days
        self.max_item_days = max_item_days


def bulk_too_many_items_detail(items: int, max_items: int) -> dict:
    """The ``detail`` of the 422 for a bulk request with more than ``max_items`` items."""
    return {"code": "bulk_too_many_items", "message": f"A bulk request may hold at most {max_items} items, not {items}", "max_items": max_items, "items": items}


def bulk_too_many_days_detail(item_days: int, max_item_days: int, *, at_least: bool = False) -> dict:
    """The ``detail`` of the 422 for a bulk request that would build more than ``max_item_days`` per-day points.

    ``at_least``: ``item_days`` is a count that stopped once past the budget, not the request's total (the conversions
    are counted one by one), and the message says so.
    """
    return {
        "code": "bulk_too_many_days",
        "message": f"A bulk request may build at most {max_item_days} per-day points, and this one would build {'at least ' if at_least else ''}{item_days}",
        "max_item_days": max_item_days,
        "item_days": item_days,
    }


def range_span_floor(end: date) -> date:
    """The first day a per-day walk ending at ``end`` may visit: ``RANGE_SPAN_LIMIT_DAYS`` before it, at most ``date.min``."""
    if (end - date.min).days <= RANGE_SPAN_LIMIT_DAYS:
        return date.min
    return end - timedelta(days=RANGE_SPAN_LIMIT_DAYS)


def stored_date_bounds() -> tuple[date, date]:
    """The first and the last date a stored price or rate may carry (X-R65, N83): ``EARLIEST_RANGE_START`` (1900-01-01,
    the floor of every replay and history walk) and ``latest_range_end()`` (tomorrow, by the server's calendar)."""
    return EARLIEST_RANGE_START, latest_range_end()


class DateOutOfRangeError(Exception):
    """A manual write holds dates outside ``stored_date_bounds()``: refused before anything is written (X-R65, N83)."""

    def __init__(self, items: list[dict], count: int, earliest: date, latest: date):
        super().__init__(f"{count} date(s) outside {earliest.isoformat()} to {latest.isoformat()}")
        self.items = items
        self.count = count
        self.earliest = earliest
        self.latest = latest


def date_out_of_range_detail(items: list[dict], count: int, earliest: date, latest: date) -> dict:
    """The ``detail`` of the 422 for a write with dates outside ``stored_date_bounds()``: at most 10 ``items``, and
    ``count`` the dates refused in all."""
    return {
        "code": "date_out_of_range",
        "message": f"Dates must lie between {earliest.isoformat()} and {latest.isoformat()}: {count} do not",
        "params": {"min": earliest.isoformat(), "max": latest.isoformat()},
        "items": items[:10],
        "count": count,
    }
