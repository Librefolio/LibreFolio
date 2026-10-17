"""
Test datetime utilities.
All test is independent of the others, so help use pytest features.
"""

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from backend.app.utils import datetime_utils
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


# ============================================================================
# TESTS: shift_date (W-B71)
# ============================================================================
#
# W-B71: three windows compute ``date ± timedelta`` on a date a request carries — promote-suggest
# (``promote_suggest_bulk``), events suggest (``suggest_events_bulk``) and the BRIM gap-fix's end of day
# (``get_balances_at_end_of``) — and raise OverflowError, a 500, at the calendar's edge. The cure is one helper,
# ``shift_date(value, days)``: the date moved by whole days, cut at date.min / date.max instead of raising.
#
# It does not exist yet, so every test that calls it looks it up first (``_shift_date``): the collection always
# succeeds, and each test fails naming what is missing. The two fixture guards pass today: they prove each expected
# value of the tables with plain ``timedelta`` arithmetic, and that each saturating case really overflows it, so once
# the helper exists a red here is about the helper, never about the table.

SHIFT_DATE_MISSING = "W-B71: backend/app/utils/datetime_utils.py has no shift_date(value, days) — the helper that moves a date by whole days and saturates at date.min / date.max instead of raising OverflowError, for the promote-suggest and events-suggest windows and the gap-fix's end of day"

# Shifts that stay inside the calendar: plain date arithmetic, whatever the month, the leap year or the edge they reach.
ORDINARY_SHIFTS = [
    pytest.param(date(2024, 6, 15), 0, date(2024, 6, 15), id="zero"),
    pytest.param(date(2026, 3, 10), -7, date(2026, 3, 3), id="a-week-back"),
    pytest.param(date(2026, 3, 10), 30, date(2026, 4, 9), id="thirty-days-on"),
    pytest.param(date(2024, 2, 28), 1, date(2024, 2, 29), id="onto-a-leap-day"),
    pytest.param(date(2024, 2, 29), 1, date(2024, 3, 1), id="off-a-leap-day"),
    pytest.param(date(2024, 3, 1), -1, date(2024, 2, 29), id="back-onto-a-leap-day"),
    pytest.param(date(2023, 2, 28), 1, date(2023, 3, 1), id="no-leap-day-in-2023"),
    pytest.param(date(1900, 2, 28), 1, date(1900, 3, 1), id="no-leap-day-in-1900"),
    pytest.param(date(2000, 2, 28), 1, date(2000, 2, 29), id="a-leap-day-in-2000"),
    pytest.param(date(2024, 4, 30), 1, date(2024, 5, 1), id="end-of-a-30-day-month"),
    pytest.param(date(2024, 5, 1), -1, date(2024, 4, 30), id="back-to-the-end-of-a-30-day-month"),
    pytest.param(date(2024, 1, 31), 30, date(2024, 3, 1), id="across-a-leap-february"),
    pytest.param(date(2024, 12, 31), 1, date(2025, 1, 1), id="end-of-the-year"),
    pytest.param(date(2025, 1, 1), -1, date(2024, 12, 31), id="back-across-the-year"),
    pytest.param(date(1, 1, 8), -7, date.min, id="exactly-onto-the-first-day"),
    pytest.param(date(9999, 12, 24), 7, date.max, id="exactly-onto-the-last-day"),
    pytest.param(date.min, 1, date(1, 1, 2), id="off-the-first-day"),
    pytest.param(date.max, -1, date(9999, 12, 30), id="off-the-last-day"),
    pytest.param(date.min, 0, date.min, id="zero-on-the-first-day"),
    pytest.param(date.max, 0, date.max, id="zero-on-the-last-day"),
]

# Shifts that would leave the calendar: cut at its edge, in the shift's direction. ±7 and ±30 are the promote-suggest
# window (tolerance_days 7 by default, 30 at most), ±1 the gap-fix's next day.
SATURATING_SHIFTS = [
    pytest.param(date.min, -1, date.min, id="a-day-before-the-first-day"),
    pytest.param(date.max, 1, date.max, id="a-day-after-the-last-day"),
    pytest.param(date(1, 1, 3), -7, date.min, id="a-week-back-from-the-third-day"),
    pytest.param(date(9999, 12, 28), 7, date.max, id="a-week-on-from-the-28th-of-december-9999"),
    pytest.param(date.min, -30, date.min, id="thirty-days-before-the-first-day"),
    pytest.param(date.max, 30, date.max, id="thirty-days-after-the-last-day"),
]


def _shift_date() -> Callable[[date, int], date]:
    """``datetime_utils.shift_date``, looked up by the test that calls it: while it is missing, that test fails naming it."""
    found = getattr(datetime_utils, "shift_date", None)
    if found is None:
        pytest.fail(SHIFT_DATE_MISSING, pytrace=False)
    return found


@pytest.mark.parametrize(("value", "days", "expected"), ORDINARY_SHIFTS)
def test_shift_date_is_plain_arithmetic_inside_the_calendar(value: date, days: int, expected: date):
    """W-B71 — red until shift_date exists: a shift that stays inside the calendar is exact, onto its edge days included."""
    shift_date = _shift_date()

    assert shift_date(value, days) == expected, f"W-B71: shift_date({value.isoformat()}, {days}) must be {expected.isoformat()}, as {value.isoformat()} + timedelta(days={days})"


@pytest.mark.parametrize(("value", "days", "expected"), SATURATING_SHIFTS)
def test_shift_date_saturates_at_the_calendars_edge(value: date, days: int, expected: date):
    """W-B71 — red until shift_date exists: a shift past the calendar's edge stops on it instead of raising OverflowError."""
    shift_date = _shift_date()

    try:
        result = shift_date(value, days)
    except OverflowError as exc:
        pytest.fail(f"W-B71: shift_date({value.isoformat()}, {days}) raised OverflowError ({exc}); past the calendar's edge it must stop on {expected.isoformat()}", pytrace=False)
    assert result == expected, f"W-B71: shift_date({value.isoformat()}, {days}) must stop on the calendar's edge, {expected.isoformat()}; got {result!r}"


def test_fixture_guard_ordinary_shifts_are_plain_arithmetic():
    """Fixture guard (passes before and after W-B71): every expected value of ORDINARY_SHIFTS is what ``timedelta`` gives."""
    for param in ORDINARY_SHIFTS:
        value, days, expected = param.values
        assert value + timedelta(days=days) == expected, param.id


def test_fixture_guard_saturating_shifts_overflow_plain_arithmetic():
    """Fixture guard (passes before and after W-B71): every SATURATING_SHIFTS case is one where ``timedelta`` raises
    OverflowError — the 500 W-B71 names — and expects the calendar's edge in the shift's direction."""
    for param in SATURATING_SHIFTS:
        value, days, expected = param.values
        with pytest.raises(OverflowError):
            value + timedelta(days=days)
        assert expected == (date.max if days > 0 else date.min), param.id


# ============================================================================
# TESTS: day_before (MF-SEC8-2b)
# ============================================================================
#
# A row stored on date.min (0001-01-01: an older version, or a hand edit; N74 refuses new rows before 1900) has no day
# before it, and ``date.min - timedelta(days=1)`` raises OverflowError. ``day_before`` answers None there: no day
# before, so nothing was held then. It is read from the module when the test runs: on a module without it (HEAD
# c0b4b6f05) only these tests fail, with AttributeError, never the module's collection.


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        pytest.param(date(2025, 1, 2), date(2025, 1, 1), id="within_a_month"),
        pytest.param(date(2025, 1, 1), date(2024, 12, 31), id="across_a_year"),
        pytest.param(date(2024, 3, 1), date(2024, 2, 29), id="across_a_leap_day"),
        pytest.param(date(1, 1, 2), date.min, id="onto_date_min"),
    ],
)
def test_day_before_is_the_previous_calendar_day(day, expected):
    """Red on HEAD c0b4b6f05 (no ``day_before``: AttributeError). Any day after date.min: the calendar day before it,
    a ``date`` — date.min itself included, as the day before 0001-01-02."""
    result = datetime_utils.day_before(day)

    assert result == expected
    assert type(result) is date


def test_day_before_date_min_is_none():
    """Red on HEAD c0b4b6f05 (no ``day_before``: AttributeError). date.min has no day before it: None, never an
    OverflowError."""
    assert datetime_utils.day_before(date.min) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
