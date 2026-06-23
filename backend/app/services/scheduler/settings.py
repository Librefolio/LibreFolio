"""Scheduler settings — read from GlobalSetting table every tick."""

from dataclasses import dataclass
from datetime import datetime, time, timezone
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_async_engine
from backend.app.services.global_settings_service import get_setting_value

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore[no-redef]


@dataclass
class SchedulerSettings:
    scheduler_enabled: bool
    current_price_frequency_minutes: int
    history_sync_times: List[time]  # UTC time objects
    history_sync_days: List[str]  # ["mon", "tue", ...]
    history_sync_horizon_days: int
    scheduler_timezone: str  # IANA timezone (for frontend display only)


def _parse_times(csv: str) -> List[time]:
    """Parse 'HH:MM,HH:MM' → list of time objects."""
    times = []
    for part in csv.split(","):
        part = part.strip()
        if part:
            h, m = part.split(":")
            times.append(time(int(h), int(m)))
    return sorted(times)


def _local_times_to_utc(local_times: List[time], tz_name: str) -> List[time]:
    """Convert a list of local times to UTC using today's date for DST offset.

    Used only for computing first-boot defaults — once times are saved they
    are already stored in UTC.
    """
    try:
        tz = ZoneInfo(tz_name)
    except (KeyError, Exception):
        return local_times  # invalid tz → assume already UTC

    today = datetime.now(timezone.utc).date()
    utc_times = []
    for t in local_times:
        local_dt = datetime(today.year, today.month, today.day, t.hour, t.minute, tzinfo=tz)
        utc_dt = local_dt.astimezone(timezone.utc)
        utc_times.append(time(utc_dt.hour, utc_dt.minute))
    return sorted(utc_times)


def _parse_days(csv: str) -> List[str]:
    """Parse 'mon,tue,wed' → list of day codes."""
    valid = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
    days = [d.strip().lower() for d in csv.split(",") if d.strip().lower() in valid]
    return days if days else ["mon", "tue", "wed", "thu", "fri", "sat"]


async def load_scheduler_settings() -> SchedulerSettings:
    """Read scheduler settings from GlobalSetting table (own session).

    Times are stored in UTC. If no times are configured yet (first boot),
    compute defaults of "06:00,23:00" in the configured timezone and convert
    to UTC before returning.
    """
    engine = get_async_engine()
    async with AsyncSession(engine) as session:
        enabled = await get_setting_value(session, "scheduler_enabled")
        freq = await get_setting_value(session, "scheduler_current_price_frequency_minutes")
        times_csv = await get_setting_value(session, "scheduler_history_sync_times")
        days_csv = await get_setting_value(session, "scheduler_history_sync_days")
        horizon = await get_setting_value(session, "scheduler_history_sync_horizon_days")
        tz_name = await get_setting_value(session, "scheduler_timezone")

    scheduler_tz = str(tz_name) if tz_name else "UTC"

    # If times are not configured yet → compute defaults in configured timezone → UTC
    if times_csv:
        sync_times = _parse_times(str(times_csv))
    else:
        default_local = _parse_times("06:00,23:00")
        sync_times = _local_times_to_utc(default_local, scheduler_tz)

    return SchedulerSettings(
        scheduler_enabled=enabled if isinstance(enabled, bool) else str(enabled).lower() == "true",
        current_price_frequency_minutes=int(freq) if freq else 10,
        history_sync_times=sync_times,
        history_sync_days=_parse_days(str(days_csv)) if days_csv else _parse_days("mon,tue,wed,thu,fri,sat"),
        history_sync_horizon_days=int(horizon) if horizon else 14,
        scheduler_timezone=scheduler_tz,
    )
