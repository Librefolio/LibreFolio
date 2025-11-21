"""
Date and time utilities for LibreFolio.

Provides timezone-aware datetime helpers and date manipulation functions.
"""
from datetime import datetime, timezone, date


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
    return datetime.now(timezone.utc)


def parse_ISO_date(v) -> date:
    if isinstance(v, date):
        return v
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, str):
        try:
            return date.fromisoformat(v)
        except ValueError as e:
            raise ValueError(f"Input must be an ISO date string (YYYY-MM-DD). Error: {e}")
    raise TypeError(f"Input must be a str, date or datetime, got {type(v)}")
