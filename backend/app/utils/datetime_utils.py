"""
Date and time utilities for LibreFolio.

Provides timezone-aware datetime helpers and date manipulation functions.
"""
from datetime import datetime, timezone


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
