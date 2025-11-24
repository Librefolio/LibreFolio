"""
Test datetime utilities.
All test is independent of the others, so help use pytest features.
"""
from datetime import datetime, timezone

import pytest

from backend.app.utils.datetime_utils import utcnow


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
    assert result.tzinfo == timezone.utc


def test_utcnow_returns_current_time():
    """Test that utcnow() returns approximately current time."""
    before = datetime.now(timezone.utc)
    result = utcnow()
    after = datetime.now(timezone.utc)

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
    assert result.tzinfo == timezone.utc
    assert result.utcoffset().total_seconds() == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
