"""Timestamp columns that are aware UTC datetimes in Python and the same plain text in SQLite (D-UTC, 1.4).

The storage is the one the plain ``DateTime`` column always wrote: the UTC clock as ``YYYY-MM-DD HH:MM:SS.ffffff``, with no
offset. So the database file, a backup, a restore and a row written by an earlier release are all read as they are: no
migration. What changes is the Python side. ``DateTime`` read that text back as a naive datetime, and every reader that
compared it to ``utcnow()`` had to remember ``ensure_utc`` (a naive-aware comparison raises ``TypeError``, and only on the
path that runs). ``UtcDateTime`` reads it back aware, with ``tzinfo=UTC``, and refuses to write a naive one: a naive
datetime has no zone, so it is not known to be UTC, and the writer is the one that must say what it meant.

SQLModel >= 0.0.48 maps a bare ``datetime`` field to its own ``UTCDateTime``, which refuses naive values and reads aware ones
back too, but stores the offset. A model field here declares ``sa_type=UtcDateTime`` so that ours is used.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


class UtcDateTime(TypeDecorator):
    """A ``DateTime`` column read back as an aware UTC datetime; a naive value is refused on write (see the module docstring)."""

    impl = DateTime
    cache_ok = True

    @property
    def python_type(self) -> type:
        return datetime

    def process_bind_param(self, value: Any, dialect: Any) -> datetime | None:
        """The value as UTC without an offset, the text the plain column always stored.

        Raises:
            ValueError: ``value`` is a datetime with no zone (naive).
            TypeError: ``value`` is not a datetime.
        """
        if value is None:
            return None
        if not isinstance(value, datetime):
            raise TypeError(f"UtcDateTime stores a datetime, not {type(value).__name__}: {value!r}")
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"UtcDateTime refuses a naive datetime, whose zone is unknown: {value!r}. Give it a zone (utcnow(), or .replace(tzinfo=UTC) when it is known to be UTC)")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: Any, dialect: Any) -> datetime | None:
        """The stored UTC clock as an aware datetime; a value that is aware already (another dialect) is converted."""
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
