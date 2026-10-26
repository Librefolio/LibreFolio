"""
Date and time utilities for LibreFolio.

Provides timezone-aware datetime helpers and date manipulation functions.
"""

from datetime import UTC, date, datetime, timedelta
from typing import Annotated

from pydantic import BeforeValidator, PlainSerializer


def utcnow() -> datetime:
    """
    Get current UTC datetime with timezone info.

    Returns:
        datetime: Current datetime in UTC with tzinfo set to timezone.utc

    Example:
        >>> now = utcnow()
        >>> now.tzinfo
        datetime.timezone.utc

    Note:
        Always use this function instead of datetime.now() to ensure
        timezone-aware timestamps across the application.
    """
    return datetime.now(UTC)


def ensure_utc(dt: datetime | str | None) -> datetime | None:
    """
    Ensure a datetime is timezone-aware (UTC).

    SQLite stores datetime as naive strings. When reading back,
    we need to add UTC timezone info if missing.

    Args:
        dt: A datetime (possibly naive), ISO string, or None

    Returns:
        A timezone-aware datetime in UTC, or None
    """
    if dt is None:
        return None

    if isinstance(dt, str):
        # Parse ISO string
        dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))

    if dt.tzinfo is None:
        # Naive datetime - assume UTC
        return dt.replace(tzinfo=UTC)

    return dt


def serialize_datetime_utc(dt: datetime | None) -> str | None:
    """
    Serialize datetime to ISO 8601 with Z suffix for UTC.

    This ensures frontend Zod validation passes (expects datetime with offset).
    """
    if dt is None:
        return None

    # Ensure timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    # Format with Z for UTC
    iso_str = dt.isoformat()

    # Replace +00:00 with Z for cleaner format
    if iso_str.endswith("+00:00"):
        iso_str = iso_str[:-6] + "Z"

    return iso_str


# Annotated type for datetime fields that need UTC serialization
# Use this in Pydantic schemas for created_at/updated_at fields
UTCDateTime = Annotated[datetime, BeforeValidator(ensure_utc), PlainSerializer(serialize_datetime_utc, return_type=str)]


def today_date() -> date:
    """
    Get current date (UTC).

    Returns:
        date: Current date in UTC

    Example:
        >>> today = today_date()
        >>> isinstance(today, date)
        True
    """
    return datetime.now(UTC).date()


def server_today() -> date:
    """Today by the server's calendar: its local date, as ``date.today()`` reads it (``today_date()`` above is UTC's).

    The day ``latest_range_end()`` follows. A broker import that keeps only settled rows compares with it (N74, the plugin
    guide's rule «the operation date, and only settled rows»): a row whose value date comes after it has not settled yet, and arrives with the next
    export.
    """
    return date.today()


def latest_range_end() -> date:
    """The latest day a requested date range may reach: tomorrow, by the server's calendar (R13-SEC7-1).

    Portfolio, lots and AI Export ranges are walked day by day, so an end far in the future held the instance for
    minutes. One day past today is the slack for a user east of the server, whose today is already the server's
    tomorrow; a later day holds no data. It is read where a range enters: ``PortfolioCalculationEngine.calculate``,
    ``PortfolioService.get_summary`` / ``get_report``, ``LotsAnalysisService.get_lots_analysis``, risk's portfolio scope
    (``risk.scope.load_scope_inputs``) and ``AiExportRuntimeService.prepare_request``.

    The server's local date, like ``date.today()`` in those modules (``today_date()`` above is UTC's): ``server_today()``
    plus one day.
    """
    return server_today() + timedelta(days=1)


def shift_date(value: date, days: int) -> date:
    """``value`` moved by ``days``, held at the calendar's ends (``date.min``, ``date.max``) instead of raising
    ``OverflowError`` (W-B71).

    For a window around a date a request or a parsed report names — the promote and event suggestions (± a tolerance),
    the days around a report set's coverage and checkpoints — whose date may sit at an edge of the calendar: such a date
    is refused when a transaction is saved (N74), but a suggestion or a check reads it, and
    ``date(1, 1, 1) - timedelta(days=1)`` raised (a 500).
    """
    try:
        return value + timedelta(days=days)
    except OverflowError:
        return date.max if days > 0 else date.min


def day_before(day: date) -> date | None:
    """The calendar day before ``day``; None for ``date.min`` (0001-01-01), which has none (MF-SEC8-2b).

    Not ``shift_date(day, -1)``: saturating would answer ``date.min`` itself, and a caller asking what was held at the
    end of the day before would count the movements of ``date.min`` as already held then. Use ``shift_date`` for a
    window's edge, which may stop at the calendar's end; use ``day_before`` where "the day before" must exist — the
    holdings an income or a cost on that day is allocated to (FIFO economic events, Yield on Cost), read as nothing held
    when it does not. A row stored on ``date.min`` by an older version made ``day - timedelta(days=1)`` raise.
    """
    return None if day == date.min else day - timedelta(days=1)


def parse_ISO_date(v) -> date:
    if isinstance(v, date):
        return v
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, str):
        try:
            return date.fromisoformat(v)
        except ValueError as e:
            raise ValueError(f"Input must be an ISO date string (YYYY-MM-DD). Error: {e}") from e
    raise TypeError(f"Input must be a str, date or datetime, got {type(v)}")
