"""The exchange's own day of a provider's row, and the one-time repair of the Yahoo rows dated the day before (Z-33).

yfinance stamps a daily bar, a dividend or a split at midnight in the exchange's timezone. Before release 1.3 the Yahoo
plugin converted that instant to UTC before taking its date: for an exchange east of UTC (Milan all year, London in
summer time, Tokyo) the stored date was the day before the session. Migration 011 marks the assignments whose rows were
stored that way (``LEGACY_UTC_DATES``); their next refresh re-dates them with ``local_date_of_legacy_utc_date``.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

#: The value of ``AssetProviderAssignment.exchange_timezone`` migration 011 writes on the assignments whose rows an
#: older version dated by UTC: not a timezone, the mark that their next fetch re-dates them once.
LEGACY_UTC_DATES = "legacy-utc"
#: The provider whose rows an older version dated by UTC: the only one migration 011 marks.
LEGACY_UTC_PROVIDER = "yfinance"


def exchange_zone(name: str | None) -> ZoneInfo | None:
    """The IANA timezone ``name`` as a ``ZoneInfo``, or None when it is empty, the legacy mark or no known zone."""
    if not name or name.strip() == LEGACY_UTC_DATES:
        return None
    try:
        return ZoneInfo(name.strip())
    except (ZoneInfoNotFoundError, ValueError):
        return None


def local_date_of_legacy_utc_date(stored: date, zone: ZoneInfo) -> date:
    """The session date of a row an older version stored on ``stored``: the UTC date of the exchange's local midnight.

    A local midnight falls on the previous UTC day exactly when the exchange is ahead of UTC at that moment, so the
    session is the next day when the zone's offset at the next day's local midnight is positive (Milan and Tokyo
    always, London in summer time only), and ``stored`` itself otherwise (New York, UTC).
    """
    following = stored + timedelta(days=1)
    offset = datetime.combine(following, time.min, tzinfo=zone).utcoffset()
    return following if offset is not None and offset > timedelta(0) else stored
