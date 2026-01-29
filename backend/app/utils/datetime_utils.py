"""
Date and time utilities for LibreFolio.

Provides timezone-aware datetime helpers and date manipulation functions.
"""

from datetime import datetime, timezone, date
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
    return datetime.now(timezone.utc)


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
        dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))

    if dt.tzinfo is None:
        # Naive datetime - assume UTC
        return dt.replace(tzinfo=timezone.utc)

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
        dt = dt.replace(tzinfo=timezone.utc)

    # Format with Z for UTC
    iso_str = dt.isoformat()

    # Replace +00:00 with Z for cleaner format
    if iso_str.endswith('+00:00'):
        iso_str = iso_str[:-6] + 'Z'

    return iso_str


# Annotated type for datetime fields that need UTC serialization
# Use this in Pydantic schemas for created_at/updated_at fields
UTCDateTime = Annotated[
    datetime,
    BeforeValidator(ensure_utc),
    PlainSerializer(serialize_datetime_utc, return_type=str)
]


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
    return datetime.now(timezone.utc).date()


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
