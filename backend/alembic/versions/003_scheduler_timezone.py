"""scheduler times use configured timezone

Revision ID: 5b1333fa6b07
Revises: 002_identifier_other_json_list
Create Date: 2026-08-31 18:02:20.082574

This data migration preserves what the user sees in the scheduler modal, not
the absolute instant. Users configured the scheduler by looking at that screen,
so the visible local wall-clock time is their intent.

Upgrade converts existing stored UTC HH:MM values into HH:MM values in
``scheduler_timezone`` and leaves configured days unchanged. For the default
``scheduler_timezone = UTC`` this is a verifiable no-op. For non-UTC installs,
the next execution instant shifts once to match the wall-clock schedule the UI
showed.

Downgrade performs the inverse conversion as a best-effort rollback. Exact
round-tripping across DST seasons is impossible because the old format stored
only HH:MM, not the date whose offset was used.
"""

from datetime import UTC, datetime, time
from typing import Sequence, Union
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import sqlalchemy as sa
from alembic import op

revision: str = "5b1333fa6b07"
down_revision: Union[str, Sequence[str], None] = "002_identifier_other_json_list"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _parse_time_csv(value: str) -> list[time]:
    parsed: list[time] = []
    for raw in value.split(","):
        part = raw.strip()
        if not part:
            continue
        hour, minute = part.split(":", 1)
        parsed.append(time(int(hour), int(minute)))
    return parsed


def _format_time_csv(times: list[time]) -> str:
    return ",".join(f"{item.hour:02d}:{item.minute:02d}" for item in sorted(times))


def _zone(tz_name: str) -> ZoneInfo | None:
    if not tz_name or tz_name == "UTC":
        return None
    try:
        return ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError):
        return None


def _convert_time_csv(value: str, tz_name: str, *, from_utc: bool) -> str:
    tz = _zone(tz_name)
    if tz is None:
        return value

    today = datetime.now(UTC).date()
    converted: list[time] = []
    for item in _parse_time_csv(value):
        source_tz = UTC if from_utc else tz
        target_tz = tz if from_utc else UTC
        source_dt = datetime(today.year, today.month, today.day, item.hour, item.minute, tzinfo=source_tz)
        target_dt = source_dt.astimezone(target_tz)
        converted.append(time(target_dt.hour, target_dt.minute))
    return _format_time_csv(converted)


def _rewrite_scheduler_times(*, from_utc: bool) -> None:
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT key, value FROM global_settings WHERE key IN ('scheduler_history_sync_times', 'scheduler_timezone')")).fetchall()
    values = {row._mapping["key"]: row._mapping["value"] for row in rows}
    times_csv = values.get("scheduler_history_sync_times")
    if not times_csv:
        return

    next_csv = _convert_time_csv(str(times_csv), str(values.get("scheduler_timezone") or "UTC"), from_utc=from_utc)
    if next_csv == times_csv:
        return

    conn.execute(sa.text("UPDATE global_settings SET value = :value WHERE key = 'scheduler_history_sync_times'"), {"value": next_csv})


def upgrade() -> None:
    """Convert stored scheduler HH:MM values from UTC into scheduler_timezone local time."""
    _rewrite_scheduler_times(from_utc=True)


def downgrade() -> None:
    """Best-effort inverse: convert scheduler local HH:MM values back to UTC."""
    _rewrite_scheduler_times(from_utc=False)
