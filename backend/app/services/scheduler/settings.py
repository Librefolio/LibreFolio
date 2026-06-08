"""Scheduler settings — read from GlobalSetting table every tick."""

from dataclasses import dataclass
from datetime import time
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_async_engine
from backend.app.services.global_settings_service import get_setting_value


@dataclass
class SchedulerSettings:
    scheduler_enabled: bool
    current_price_frequency_minutes: int
    history_sync_times: List[time]  # parsed from CSV "HH:MM,HH:MM"
    history_sync_days: List[str]  # ["mon", "tue", ...]
    history_sync_horizon_days: int


def _parse_times(csv: str) -> List[time]:
    """Parse 'HH:MM,HH:MM' → list of time objects."""
    times = []
    for part in csv.split(","):
        part = part.strip()
        if part:
            h, m = part.split(":")
            times.append(time(int(h), int(m)))
    return sorted(times)


def _parse_days(csv: str) -> List[str]:
    """Parse 'mon,tue,wed' → list of day codes."""
    valid = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
    days = [d.strip().lower() for d in csv.split(",") if d.strip().lower() in valid]
    return days if days else ["mon", "tue", "wed", "thu", "fri", "sat"]


async def load_scheduler_settings() -> SchedulerSettings:
    """Read scheduler settings from GlobalSetting table (own session)."""
    engine = get_async_engine()
    async with AsyncSession(engine) as session:
        enabled = await get_setting_value(session, "scheduler_enabled")
        freq = await get_setting_value(session, "scheduler_current_price_frequency_minutes")
        times_csv = await get_setting_value(session, "scheduler_history_sync_times")
        days_csv = await get_setting_value(session, "scheduler_history_sync_days")
        horizon = await get_setting_value(session, "scheduler_history_sync_horizon_days")

    return SchedulerSettings(
        scheduler_enabled=enabled if isinstance(enabled, bool) else str(enabled).lower() == "true",
        current_price_frequency_minutes=int(freq) if freq else 10,
        history_sync_times=_parse_times(str(times_csv)) if times_csv else _parse_times("06:00,23:00"),
        history_sync_days=_parse_days(str(days_csv)) if days_csv else _parse_days("mon,tue,wed,thu,fri,sat"),
        history_sync_horizon_days=int(horizon) if horizon else 14,
    )
