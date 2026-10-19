"""The exchange's own day of a provider's row, and the one-time repair of the Yahoo rows dated the day before (Z-33).

yfinance stamps a daily bar, a dividend or a split at midnight in the exchange's timezone. Before release 1.3 the Yahoo
plugin converted that instant to UTC before taking its date: for an exchange east of UTC (Milan all year, London in
summer time, Tokyo) the stored date was the day before the session. Migration 011 marks the assignments whose rows were
stored that way (``LEGACY_UTC_DATES``); their next refresh re-dates them with ``local_date_of_legacy_utc_date``.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import structlog

#: The value of ``AssetProviderAssignment.exchange_timezone`` migration 011 writes on the assignments whose rows an
#: older version dated by UTC: not a timezone, the mark that their next fetch re-dates them once.
LEGACY_UTC_DATES = "legacy-utc"
#: The provider whose rows an older version dated by UTC: the only one migration 011 marks.
LEGACY_UTC_PROVIDER = "yfinance"


logger = structlog.get_logger(__name__)

#: The unknown Area/Location names already logged by ``exchange_zone``, once per name and process
_UNKNOWN_ZONES_LOGGED: set[str] = set()


def exchange_zone(name: str | None) -> ZoneInfo | None:
    """The IANA timezone ``name`` as a ``ZoneInfo``, or None when it is empty, the legacy mark or no known zone.

    An Area/Location name (``Europe/Rome``) the server's timezone database does not know is logged once per name and
    process: on a host without one (Windows without the ``tzdata`` package, a minimal container) a Yahoo assignment
    still marked by migration 011 writes nothing until the name resolves (backlog Z-36). A fixed offset or another
    name without an area is not logged: no timezone database has it.
    """
    if not name or name.strip() == LEGACY_UTC_DATES:
        return None
    key = name.strip()
    try:
        return ZoneInfo(key)
    except ZoneInfoNotFoundError:
        if "/" in key and key not in _UNKNOWN_ZONES_LOGGED:
            _UNKNOWN_ZONES_LOGGED.add(key)
            logger.warning("Exchange timezone unknown to this server's timezone database: the stored dates awaiting their one-time check stay as they are until it resolves", timezone=key[:64])
        return None
    except ValueError:
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
