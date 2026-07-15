"""
Small coverage tests for scheduler settings helpers.
"""

from datetime import UTC, datetime, time

from backend.app.services.scheduler import settings as scheduler_settings


class FixedWinterDateTime(datetime):
    """Freeze today() for deterministic timezone conversion."""

    @classmethod
    def now(cls, tz=None):
        current = cls(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
        return current if tz is None else current.astimezone(tz)


def test_local_times_to_utc_converts_europe_rome_in_winter(monkeypatch):
    """Europe/Rome winter offset is UTC+1."""
    monkeypatch.setattr(scheduler_settings, "datetime", FixedWinterDateTime)

    result = scheduler_settings._local_times_to_utc(
        [time(23, 30), time(6, 0)],
        "Europe/Rome",
    )

    assert result == [time(5, 0), time(22, 30)]


def test_local_times_to_utc_converts_america_new_york_in_winter(monkeypatch):
    """America/New_York winter offset is UTC-5."""
    monkeypatch.setattr(scheduler_settings, "datetime", FixedWinterDateTime)

    result = scheduler_settings._local_times_to_utc([time(9, 0)], "America/New_York")

    assert result == [time(14, 0)]
