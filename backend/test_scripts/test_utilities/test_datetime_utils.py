"""
Test datetime utilities.
All test is independent of the others, so help use pytest features.
"""

from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from backend.app.utils.datetime_utils import ensure_utc, parse_ISO_date, serialize_datetime_utc, utcnow

# ============================================================================
# TESTS: utcnow
# ============================================================================


def test_utcnow_returns_datetime():
    """Test that utcnow() returns a datetime object."""
    result = utcnow()
    assert isinstance(result, datetime)


def test_utcnow_has_timezone_info():
    """Test that utcnow() returns timezone-aware datetime."""
    result = utcnow()
    assert result.tzinfo is not None
    assert result.tzinfo == UTC


def test_utcnow_returns_current_time():
    """Test that utcnow() returns approximately current time."""
    before = datetime.now(UTC)
    result = utcnow()
    after = datetime.now(UTC)

    # Result should be between before and after (within same second)
    assert before <= result <= after


def test_utcnow_multiple_calls():
    """Test that multiple calls to utcnow() return increasing times."""
    first = utcnow()
    second = utcnow()

    # Second call should be same or later than first
    assert second >= first


def test_utcnow_tzinfo_is_utc():
    """Test that utcnow() specifically returns UTC timezone."""
    result = utcnow()
    assert result.tzinfo == UTC
    assert result.utcoffset().total_seconds() == 0


def test_ensure_utc_adds_timezone_to_naive_datetime():
    """Test that ensure_utc() assumes UTC for naive datetimes."""
    naive = datetime(2025, 1, 1, 12, 30, 45)

    result = ensure_utc(naive)

    assert result == datetime(2025, 1, 1, 12, 30, 45, tzinfo=UTC)


def test_ensure_utc_parses_iso_string():
    """Test that ensure_utc() parses ISO strings with Z suffix."""
    result = ensure_utc("2025-01-01T12:30:45Z")

    assert result == datetime(2025, 1, 1, 12, 30, 45, tzinfo=UTC)


def test_serialize_datetime_utc_normalizes_utc_suffix():
    """Test that serialize_datetime_utc() emits Z for UTC datetimes."""
    result = serialize_datetime_utc(datetime(2025, 1, 1, 12, 30, 45, tzinfo=UTC))

    assert result == "2025-01-01T12:30:45Z"


def test_serialize_datetime_utc_adds_utc_to_naive_datetime():
    """Test that serialize_datetime_utc() assumes UTC for naive datetimes."""
    result = serialize_datetime_utc(datetime(2025, 1, 1, 12, 30, 45))

    assert result == "2025-01-01T12:30:45Z"


def test_serialize_datetime_utc_preserves_non_utc_offset():
    """Test that serialize_datetime_utc() keeps non-UTC offsets unchanged."""
    result = serialize_datetime_utc(datetime(2025, 1, 1, 12, 30, 45, tzinfo=timezone(timedelta(hours=2))))

    assert result == "2025-01-01T12:30:45+02:00"


def test_parse_iso_date_accepts_string_and_date():
    """Test that parse_ISO_date() handles string and date inputs."""
    assert parse_ISO_date("2025-01-01") == date(2025, 1, 1)
    assert parse_ISO_date(date(2025, 1, 3)) == date(2025, 1, 3)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
