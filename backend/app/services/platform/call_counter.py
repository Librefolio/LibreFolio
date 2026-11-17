"""How many calls a plugin made to its external service, and the instance's limits on them (project 76, U1; plan §3.5).

One row per plugin, or per shared group (``family="group"``), in ``plugin_call_counters``: five calendar windows aligned
in UTC — minute (hh:mm:00), hour (hh:00), day (00:00), ISO week (Monday 00:00), month (day 1, 00:00) — each with the
start of the window its count belongs to (``<window>_since``, epoch seconds) and the count.

- **One statement per call, atomic.** ``count_and_check`` runs one ``INSERT … ON CONFLICT … DO UPDATE … WHERE …
  RETURNING``: SQLite runs a statement whole and takes the file's write lock for it, so the count is exact across
  uvicorn workers and processes that share the database. A window whose ``since`` is older than the window of now
  restarts at 1; ``since`` never moves back (``MAX``), so a clock set back counts into the stored window.
- **A full window refuses the call, and does not count it.** The ``WHERE`` fails, nothing is written and nothing is
  returned; only then a ``SELECT`` reads which windows are full. ``CallLimitReached`` names the one that ends last
  (retrying before it ends is useless), its limit, its count, its end and the seconds until then. A limit of 0 stops
  the plugin: refused before the statement. No limit (None) never refuses.
- **Its own short transaction**, separate from the caller's session: a boundary may hold one open.
- **A counter never stops a price.** When the database fails (a lock past ``busy_timeout``, a full disk), the call goes
  anyway: one warning, and None.
- **Reading never writes** (``read_counts``, for the settings page): a window older than now's reads 0, no row reads 0.

Every call through a core boundary counts +1 BEFORE it leaves, failed or not (U2, U3; the enrichers in K1).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, case, func, select, true
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc import SQLAlchemyError

from backend.app.db.models import PluginCallCounter
from backend.app.db.session import get_async_engine
from backend.app.logging_config import get_logger

logger = get_logger(__name__)

#: The five windows, shortest first.
WINDOWS = ("minute", "hour", "day", "week", "month")


@dataclass(frozen=True)
class CallLimits:
    """The most calls each window admits: None, no limit; 0, the plugin is stopped."""

    minute: int | None = None
    hour: int | None = None
    day: int | None = None
    week: int | None = None
    month: int | None = None


@dataclass(frozen=True)
class CallCounts:
    """The calls of each window of now."""

    minute: int
    hour: int
    day: int
    week: int
    month: int


ZERO = CallCounts(0, 0, 0, 0, 0)


class CallLimitReached(Exception):
    """A window of the plugin is full: the call does not leave. ``window`` is the full window that ends last."""

    def __init__(self, family: str, plugin_code: str, window: str, limit: int, count: int, resets_at: datetime, retry_after: float) -> None:
        self.family = family
        self.plugin_code = plugin_code
        self.window = window
        self.limit = limit
        self.count = count
        self.resets_at = resets_at
        self.retry_after = retry_after
        super().__init__(f"Call limit reached for {family}/{plugin_code}: {window} {count}/{limit}, until {resets_at.isoformat()}")


def _utc(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(UTC)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError(f"call_counter needs an aware datetime, not {now!r}")
    return now.astimezone(UTC)


def _start_of(window: str, moment: datetime) -> datetime:
    """The start of ``window`` holding ``moment`` (aware, UTC)."""
    if window == "minute":
        return moment.replace(second=0, microsecond=0)
    if window == "hour":
        return moment.replace(minute=0, second=0, microsecond=0)
    day = moment.replace(hour=0, minute=0, second=0, microsecond=0)
    if window == "day":
        return day
    if window == "week":
        return day - timedelta(days=day.weekday())
    if window == "month":
        return day.replace(day=1)
    raise ValueError(f"Unknown window {window!r}")


def window_starts(now: datetime) -> dict[str, int]:
    """The start of each window holding ``now``, as epoch seconds (UTC)."""
    moment = _utc(now)
    return {window: int(_start_of(window, moment).timestamp()) for window in WINDOWS}


def window_end(window: str, start: int) -> datetime:
    """The end of the window that starts at ``start`` (epoch seconds): the start of the next one, aware UTC."""
    begin = datetime.fromtimestamp(start, UTC)
    if window == "minute":
        return begin + timedelta(minutes=1)
    if window == "hour":
        return begin + timedelta(hours=1)
    if window == "day":
        return begin + timedelta(days=1)
    if window == "week":
        return begin + timedelta(weeks=1)
    if window == "month":
        return begin.replace(year=begin.year + 1, month=1) if begin.month == 12 else begin.replace(month=begin.month + 1)
    raise ValueError(f"Unknown window {window!r}")


def _refusal(family: str, plugin_code: str, full: list[tuple[str, int, int]], starts: dict[str, int], moment: datetime) -> CallLimitReached:
    """The refusal naming, among the full windows ``(window, limit, count)``, the one that ends last."""
    window, limit, count = max(full, key=lambda item: window_end(item[0], starts[item[0]]))
    resets_at = window_end(window, starts[window])
    return CallLimitReached(family, plugin_code, window, limit, count, resets_at, max((resets_at - moment).total_seconds(), 0.001))


def _current(row: PluginCallCounter | None, starts: dict[str, int]) -> CallCounts:
    """The counts of the windows of now: a stored window older than now's is 0."""
    if row is None:
        return ZERO
    return CallCounts(**{window: getattr(row, f"{window}_count") if getattr(row, f"{window}_since") >= starts[window] else 0 for window in WINDOWS})


async def count_and_check(family: str, plugin_code: str, limits: CallLimits | None = None, *, now: datetime | None = None) -> CallCounts | None:
    """Count one call of ``family``/``plugin_code`` and return the counts after it, or raise ``CallLimitReached`` when a
    window is full (nothing counted). None when the database fails: the call goes anyway, and the log says so."""
    moment = _utc(now)
    starts = window_starts(moment)
    caps = {window: getattr(limits, window) if limits is not None else None for window in WINDOWS}
    stopped = [(window, 0, 0) for window, cap in caps.items() if cap == 0]
    table = PluginCallCounter.__table__
    if stopped:
        # A stopped plugin is refused whatever the database does; the count, for the message, is 0 when it cannot be read
        try:
            async with get_async_engine().connect() as connection:
                row = (await connection.execute(select(table).where(table.c.family == family, table.c.plugin_code == plugin_code))).first()
        except SQLAlchemyError as error:
            logger.warning("Plugin call counts not read for a stopped plugin: database error, refused anyway", family=family, plugin=plugin_code, error=type(error).__name__)
            row = None
        counts = _current(row, starts)
        raise _refusal(family, plugin_code, [(window, 0, getattr(counts, window)) for window, _cap, _count in stopped], starts, moment)
    try:
        after = {window: case((table.c[f"{window}_since"] < starts[window], 1), else_=table.c[f"{window}_count"] + 1) for window in WINDOWS}
        guard = and_(true(), *(after[window] <= cap for window, cap in caps.items() if cap is not None))
        values = {"family": family, "plugin_code": plugin_code, "updated_at": moment}
        for window in WINDOWS:
            values[f"{window}_since"] = starts[window]
            values[f"{window}_count"] = 1
        update = {"updated_at": moment}
        for window in WINDOWS:
            update[f"{window}_count"] = after[window]
            update[f"{window}_since"] = func.max(table.c[f"{window}_since"], starts[window])
        statement = insert(table).values(**values).on_conflict_do_update(index_elements=["family", "plugin_code"], set_=update, where=guard).returning(*(table.c[f"{window}_count"] for window in WINDOWS))
        async with get_async_engine().begin() as connection:
            counted = (await connection.execute(statement)).first()
            if counted is None:
                row = (await connection.execute(select(table).where(table.c.family == family, table.c.plugin_code == plugin_code))).first()
    except SQLAlchemyError as error:
        logger.warning("Plugin call not counted: database error, the call goes anyway", family=family, plugin=plugin_code, error=type(error).__name__, exc_info=error)
        return None
    if counted is not None:
        return CallCounts(*counted)
    current = _current(row, starts)
    full = [(window, cap, getattr(current, window)) for window, cap in caps.items() if cap is not None and getattr(current, window) + 1 > cap]
    if not full:  # the SELECT read the row the WHERE judged, in the same transaction: not expected, never a refusal
        logger.warning("Plugin call refused by the counter without a full window: the call goes anyway", family=family, plugin=plugin_code)
        return None
    raise _refusal(family, plugin_code, full, starts, moment)


async def read_counts(family: str, plugin_code: str, *, now: datetime | None = None) -> CallCounts:
    """The counts of the windows of now, read without writing: a stale window reads 0, no row reads all 0."""
    starts = window_starts(_utc(now))
    table = PluginCallCounter.__table__
    async with get_async_engine().connect() as connection:
        row = (await connection.execute(select(table).where(table.c.family == family, table.c.plugin_code == plugin_code))).first()
    return _current(row, starts)
