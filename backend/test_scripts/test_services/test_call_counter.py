"""The per-instance call counter of the plugins that call an external service (project 76, lot U1; plan 76, §3.5).

Module under test: ``backend/app/services/platform/call_counter.py``. One row of ``plugin_call_counters`` per
(``family``, ``plugin_code``) — the code may be a shared group's name, family ``group`` —, five calendar windows aligned
in UTC, each a start (``<w>_since``, epoch seconds) and a count (``<w>_count``). U2/U3 call the helper at the core
boundaries; U1 delivers the helper and the table only.

The contract pinned here:

0. Names: ``WINDOWS == ("minute", "hour", "day", "week", "month")``; ``CallLimits`` (frozen dataclass, every window
   ``int | None`` defaulting to None: None no limit, 0 stopped), ``CallCounts`` (frozen dataclass, five ints),
   ``CallLimitReached(Exception)`` with ``family``, ``plugin_code``, ``window``, ``limit``, ``count``, ``resets_at``
   (aware UTC) and ``retry_after`` (float seconds > 0); ``count_and_check(family, plugin_code, limits=None, *,
   now=None)`` and ``read_counts(family, plugin_code, *, now=None)``, both coroutines; ``logger`` the module's structlog
   logger; ``get_async_engine`` reached as a module attribute at call time (the tests patch it).
   ``now`` omitted → ``datetime.now(UTC)``.
1. ``window_starts(now)``: epoch seconds of each window's start for an aware ``now`` in any zone, read in UTC: minute
   hh:mm:00, hour hh:00, day 00:00, week the ISO Monday 00:00, month day 1 00:00. A Sunday 23:59:59 belongs to the week
   of the previous Monday; Monday 00:00:00 starts a new week; 31 December → 1 January rolls month and year.
2. ``window_end(window, start)``: the aware UTC start of the next window; a month of 28, 29, 30 or 31 days, December
   into January.
3. First call → the row inserted with every count 1 and the five starts of ``now``, ``updated_at`` = ``now`` (read back
   through the model's column); the call returns ``CallCounts`` all 1.
4. Calls inside the same windows add one to each count.
5. A window change resets exactly that window and the smaller ones: next minute; next hour; next day; a new ISO week
   (Sunday → Monday, mid-month); a new month (Monday → Tuesday, mid-week: the week keeps counting).
6. A ``now`` earlier than a stored start (clock moved back) never lowers it (MAX) and counts into the stored window.
7. Limits: with ``minute=3`` calls 1–3 pass, the 4th raises ``CallLimitReached(window="minute", limit=3, count=3)``,
   the row unchanged (``updated_at`` too), ``resets_at`` the next minute, ``retry_after`` the seconds to it; in the next
   minute the call passes again (the rolled count is 1). Same for a month limit. Several full windows → the one ending
   last is named.
8. Limit 0 → refused before the statement: no row created when none existed (count 0), an existing row unchanged (count
   its current count or 0, the contract allows both); the window named is the longest one whose limit is 0.
9. ``limits`` None, or every window None → never refused.
10. Rows of different (``family``, ``plugin_code``) are independent; family ``group`` works like any.
11. Two processes counting one row of one SQLite file at once (WAL, busy_timeout, the production PRAGMAs): 2 × 50 calls
    → 100, every count 1..100 returned exactly once (no lost update); with ``minute=60`` exactly 60 calls pass across
    both, every count 1..60 returned once, 40 refused, the row at 60.
12. The database failing (``SQLAlchemyError``: a file in a missing folder, a table missing) → ``None``, one warning
    from ``call_counter.logger`` naming family and plugin, nothing raised.
13. ``read_counts`` never writes: no row → all zeros (and still no row); a row → its counts, a window whose start is
    older than the current window's reads 0; the row unchanged, ``updated_at`` included.
14. (U2) The counter's own ``busy_timeout``, ``COUNTER_BUSY_TIMEOUT_MS = 2000``, on its connection only: set at the
    start of each counter transaction, the connection's previous value restored after it. Another connection holding
    ``BEGIN IMMEDIATE`` makes ``count_and_check`` return None in about 2 s, not the session listener's 30; a pooled
    connection reads 30 000 again after a counted, a refused and a timed-out call.
15. (U2) The database-failure warning is written at most once a minute per (``family``, ``plugin_code``), the limit-0
    path's included: the clock is ``call_counter._monotonic`` (``time.monotonic``), the memory ``_warned_at`` (a dict).

Isolation: PURE. No lane database, no server, no network: every database is a private SQLite file under ``tmp_path``,
built by ``SQLModel.metadata.create_all``; ``call_counter.get_async_engine`` is patched to that file's engine, and
``backend.app.db.session.get_async_engine`` / ``get_sync_engine`` are tripwires. The two child processes of (11) run a
script written under ``tmp_path``, inherit this process's environment (``TMPDIR`` the lane's), point the counter at
the private file, and are started together behind a ready/go barrier on their stdin.

Red on HEAD f2464fb32: ``backend.app.services.platform.call_counter`` does not exist and the models declare no
``plugin_call_counters``. Every test reaches the module through ``_counter_module()``, which fails the test (not a
fixture, not the collection) with «red until U1»; fixtures only build and dispose private files and engines.
"""

from __future__ import annotations

import asyncio
import dataclasses
import importlib
import inspect
import json
import os
import sqlite3
import subprocess
import sys
import time
from collections.abc import AsyncIterator, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, NoReturn, Optional

import pytest
import pytest_asyncio
from sqlalchemy import create_engine, event, select
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool
from structlog.testing import capture_logs

from backend.app.config import PROJECT_ROOT
from backend.app.db import session as db_session
from backend.app.db.base import SQLModel

MODULE = "backend.app.services.platform.call_counter"
TABLE = "plugin_call_counters"
WINDOWS = ("minute", "hour", "day", "week", "month")
LOG_CANARY = "call counter test: the capture reaches the counter's logger"

# Imported here, before any test sets the session's tripwires: imported first inside a test, a module that binds
# ``from backend.app.db.session import get_async_engine`` would bind the tripwire, and monkeypatch would restore it
# there for every later test of the process. On HEAD the module is missing: each test fails on it in its own body.
try:
    importlib.import_module(MODULE)
except ModuleNotFoundError as _missing:
    if _missing.name != MODULE:
        raise

#: A Tuesday afternoon, mid-month: every window's start is a different instant.
NOW = datetime(2026, 11, 17, 13, 45, 30, tzinfo=UTC)


def _utc(*parts: int) -> datetime:
    return datetime(*parts, tzinfo=UTC)


def _epoch(*parts: int) -> int:
    return int(_utc(*parts).timestamp())


def _expected_starts(now: datetime) -> dict[str, int]:
    """The test's own reading of the five window starts of ``now`` (the module's ``window_starts`` is pinned by
    literals in section 1)."""
    minute = now.astimezone(UTC).replace(second=0, microsecond=0)
    hour = minute.replace(minute=0)
    day = hour.replace(hour=0)
    week = day - timedelta(days=day.weekday())
    month = day.replace(day=1)
    return {name: int(start.timestamp()) for name, start in zip(WINDOWS, (minute, hour, day, week, month), strict=True)}


def _weekday_barrier(moment: datetime, weekday: int) -> None:
    assert moment.weekday() == weekday, f"setup: {moment.isoformat()} is weekday {moment.weekday()}, not {weekday}"


# =============================================================================
# HELPERS — the module, the private database, the log
# =============================================================================


def _lane_database_tripwire(*_arguments: object, **_keywords: object) -> NoReturn:
    raise AssertionError("the lane's engine was asked for: this module works on its private files only")


@pytest.fixture(autouse=True)
def no_lane_database(monkeypatch: pytest.MonkeyPatch) -> None:
    """``get_async_engine`` and ``get_sync_engine`` of the session module raise: every database here is a private file."""
    monkeypatch.setattr(db_session, "get_async_engine", _lane_database_tripwire, raising=False)
    monkeypatch.setattr(db_session, "get_sync_engine", _lane_database_tripwire, raising=False)


def _counter_module() -> ModuleType:
    """``call_counter``, or the test fails with the reason: red until U1."""
    try:
        return importlib.import_module(MODULE)
    except ModuleNotFoundError as missing:
        if missing.name != MODULE:
            raise
        pytest.fail(f"red until U1: {MODULE} does not exist", pytrace=False)


def _pure(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """The module, its engine a tripwire: for the functions that must not touch a database."""
    module = _counter_module()
    monkeypatch.setattr(module, "get_async_engine", _lane_database_tripwire, raising=True)
    return module


@dataclass(frozen=True)
class Private:
    """A private SQLite file under ``tmp_path``, built by ``create_all``, and the async engine on it."""

    path: Path
    engine: AsyncEngine


def _build_by_models(path: Path) -> None:
    engine = create_engine(f"sqlite:///{path}", poolclass=NullPool)
    try:
        SQLModel.metadata.create_all(engine)
    finally:
        engine.dispose()


@pytest_asyncio.fixture
async def private(tmp_path: Path) -> AsyncIterator[Private]:
    """A new private database (``create_all``: on HEAD it has no counter table, ``_bound`` says so) and its engine."""
    path = tmp_path / "counters.db"
    _build_by_models(path)
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}", poolclass=NullPool)
    try:
        yield Private(path, engine)
    finally:
        await engine.dispose()


def _table_barrier(path: Path) -> None:
    assert TABLE in SQLModel.metadata.tables, f"red until U1: the models declare no {TABLE}"
    engine = create_engine(f"sqlite:///{path}", poolclass=NullPool)
    try:
        with engine.connect() as conn:
            found = conn.exec_driver_sql("SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?", (TABLE,)).first()
    finally:
        engine.dispose()
    assert found is not None, f"setup: create_all built no {TABLE} in {path.name}"


def _bound(monkeypatch: pytest.MonkeyPatch, db: Private) -> ModuleType:
    """The module, its ``get_async_engine`` the private file's engine; barrier: the counter table is there."""
    module = _counter_module()
    _table_barrier(db.path)
    monkeypatch.setattr(module, "get_async_engine", lambda: db.engine, raising=True)
    return module


def _row(path: Path, family: str, plugin_code: str) -> Optional[dict[str, Any]]:
    """The counter row of the pair, read through the model's table (``updated_at`` an aware UTC datetime), or None."""
    table = SQLModel.metadata.tables[TABLE]
    engine = create_engine(f"sqlite:///{path}", poolclass=NullPool)
    try:
        with engine.connect() as conn:
            found = conn.execute(select(table).where(table.c.family == family, table.c.plugin_code == plugin_code)).mappings().first()
    finally:
        engine.dispose()
    return dict(found) if found is not None else None


def _row_count(path: Path) -> int:
    engine = create_engine(f"sqlite:///{path}", poolclass=NullPool)
    try:
        with engine.connect() as conn:
            return conn.exec_driver_sql(f"SELECT count(*) FROM {TABLE}").scalar_one()
    finally:
        engine.dispose()


def _stored_counts(row: dict[str, Any]) -> tuple[int, ...]:
    return tuple(row[f"{window}_count"] for window in WINDOWS)


def _stored_starts(row: dict[str, Any]) -> dict[str, int]:
    return {window: row[f"{window}_since"] for window in WINDOWS}


def _counts(module: ModuleType, minute: int, hour: int, day: int, week: int, month: int) -> Any:
    return module.CallCounts(minute=minute, hour=hour, day=day, week=week, month=month)


async def _call(module: ModuleType, family: str, plugin_code: str, when: datetime, limits: Any = None) -> Any:
    return await module.count_and_check(family, plugin_code, limits, now=when)


async def _refusal(module: ModuleType, family: str, plugin_code: str, when: datetime, limits: Any) -> Any:
    with pytest.raises(module.CallLimitReached) as refused:
        await module.count_and_check(family, plugin_code, limits, now=when)
    return refused.value


def _assert_refusal(error: Any, *, family: str, plugin_code: str, window: str, limit: int, count: Any, resets_at: datetime, now: datetime) -> None:
    """Every attribute of ``CallLimitReached``; ``count`` an int or a set of the values the contract allows."""
    found = (error.family, error.plugin_code, error.window, error.limit)
    assert found == (family, plugin_code, window, limit), f"(family, plugin_code, window, limit) {found}, expected {(family, plugin_code, window, limit)}"
    allowed = count if isinstance(count, set) else {count}
    assert error.count in allowed, f"count {error.count}, expected one of {sorted(allowed)}"
    assert error.resets_at == resets_at, f"resets_at {error.resets_at}, expected {resets_at}"
    assert error.resets_at.utcoffset() == timedelta(0), f"resets_at must be aware UTC: {error.resets_at!r}"
    expected_wait = (resets_at - now).total_seconds()
    assert isinstance(error.retry_after, float) and error.retry_after > 0, f"retry_after must be a positive float: {error.retry_after!r}"
    assert error.retry_after == pytest.approx(expected_wait), f"retry_after {error.retry_after}, expected {expected_wait}"


@contextmanager
def _captured(module: ModuleType) -> Iterator[list[dict[str, Any]]]:
    """The structlog events of the block, behind a barrier: a canary logged through ``call_counter.logger`` is there."""
    with capture_logs() as events:
        module.logger.debug(LOG_CANARY)
        yield events
    assert any(event.get("event") == LOG_CANARY for event in events), f"barrier: the counter's logger does not reach capture_logs: {events}"


# =============================================================================
# 0. THE NAMES
# =============================================================================


def test_u1_the_module_exposes_its_names_and_signatures(monkeypatch: pytest.MonkeyPatch) -> None:
    """``WINDOWS``; the two frozen dataclasses with their fields and defaults; the exception; both functions coroutines
    with ``now`` keyword-only and no session parameter (the helper opens its own connection)."""
    module = _pure(monkeypatch)
    assert module.WINDOWS == WINDOWS, f"WINDOWS {module.WINDOWS}"
    for name in ("CallLimits", "CallCounts"):
        cls = getattr(module, name)
        assert dataclasses.is_dataclass(cls) and cls.__dataclass_params__.frozen, f"{name} must be a frozen dataclass"
        assert tuple(field.name for field in dataclasses.fields(cls)) == WINDOWS, f"{name} fields {[f.name for f in dataclasses.fields(cls)]}"
    assert module.CallLimits() == module.CallLimits(minute=None, hour=None, day=None, week=None, month=None), "every limit defaults to None"
    assert issubclass(module.CallLimitReached, Exception)
    for name, expected in (("count_and_check", ["family", "plugin_code", "limits", "now"]), ("read_counts", ["family", "plugin_code", "now"])):
        function = getattr(module, name)
        assert inspect.iscoroutinefunction(function), f"{name} must be async"
        parameters = inspect.signature(function).parameters
        assert list(parameters) == expected, f"{name}{inspect.signature(function)}, expected parameters {expected}"
        assert parameters["now"].kind is inspect.Parameter.KEYWORD_ONLY and parameters["now"].default is None, f"{name}: now keyword-only, default None"
    assert inspect.signature(module.count_and_check).parameters["limits"].default is None, "count_and_check: limits defaults to None"


# =============================================================================
# 1. window_starts
# =============================================================================


WINDOW_STARTS = [
    pytest.param(
        NOW,
        {"minute": _epoch(2026, 11, 17, 13, 45), "hour": _epoch(2026, 11, 17, 13), "day": _epoch(2026, 11, 17), "week": _epoch(2026, 11, 16), "month": _epoch(2026, 11, 1)},
        id="tuesday-afternoon",
    ),
    pytest.param(
        _utc(2026, 11, 22, 23, 59, 59),
        {"minute": _epoch(2026, 11, 22, 23, 59), "hour": _epoch(2026, 11, 22, 23), "day": _epoch(2026, 11, 22), "week": _epoch(2026, 11, 16), "month": _epoch(2026, 11, 1)},
        id="sunday-last-second-is-in-the-week-of-the-previous-monday",
    ),
    pytest.param(
        _utc(2026, 11, 23, 0, 0, 0),
        {"minute": _epoch(2026, 11, 23), "hour": _epoch(2026, 11, 23), "day": _epoch(2026, 11, 23), "week": _epoch(2026, 11, 23), "month": _epoch(2026, 11, 1)},
        id="monday-midnight-starts-a-new-week",
    ),
    pytest.param(
        _utc(2026, 12, 31, 23, 59, 59),
        {"minute": _epoch(2026, 12, 31, 23, 59), "hour": _epoch(2026, 12, 31, 23), "day": _epoch(2026, 12, 31), "week": _epoch(2026, 12, 28), "month": _epoch(2026, 12, 1)},
        id="new-years-eve",
    ),
    pytest.param(
        _utc(2027, 1, 1, 0, 0, 0),
        {"minute": _epoch(2027, 1, 1), "hour": _epoch(2027, 1, 1), "day": _epoch(2027, 1, 1), "week": _epoch(2026, 12, 28), "month": _epoch(2027, 1, 1)},
        id="new-year-rolls-month-and-year-not-the-week",
    ),
    pytest.param(
        datetime(2026, 11, 17, 1, 30, 15, tzinfo=timezone(timedelta(hours=2))),
        {"minute": _epoch(2026, 11, 16, 23, 30), "hour": _epoch(2026, 11, 16, 23), "day": _epoch(2026, 11, 16), "week": _epoch(2026, 11, 16), "month": _epoch(2026, 11, 1)},
        id="plus-two-hours-read-in-utc-the-day-before",
    ),
    pytest.param(
        datetime(2026, 12, 1, 0, 30, tzinfo=timezone(timedelta(hours=1))),
        {"minute": _epoch(2026, 11, 30, 23, 30), "hour": _epoch(2026, 11, 30, 23), "day": _epoch(2026, 11, 30), "week": _epoch(2026, 11, 30), "month": _epoch(2026, 11, 1)},
        id="plus-one-hour-on-the-first-is-still-last-month-in-utc",
    ),
]


@pytest.mark.parametrize(("now", "expected"), WINDOW_STARTS)
def test_u1_window_starts(monkeypatch: pytest.MonkeyPatch, now: datetime, expected: dict[str, int]) -> None:
    """The five starts of ``now``, read in UTC, as epoch seconds; the calendar itself checked first (weekday barriers)."""
    _weekday_barrier(_utc(2026, 11, 16), 0)
    _weekday_barrier(_utc(2026, 11, 22), 6)
    _weekday_barrier(_utc(2026, 12, 28), 0)
    _weekday_barrier(_utc(2026, 11, 30), 0)
    module = _pure(monkeypatch)
    found = module.window_starts(now)
    assert found == expected, f"window_starts({now.isoformat()}): {found}, expected {expected}"
    assert all(type(value) is int for value in found.values()), f"epoch seconds as int: {found}"


WINDOW_ENDS = [
    pytest.param("minute", _utc(2026, 11, 17, 13, 45), _utc(2026, 11, 17, 13, 46), id="minute"),
    pytest.param("minute", _utc(2026, 12, 31, 23, 59), _utc(2027, 1, 1), id="minute-into-the-new-year"),
    pytest.param("hour", _utc(2026, 11, 17, 13), _utc(2026, 11, 17, 14), id="hour"),
    pytest.param("day", _utc(2026, 11, 17), _utc(2026, 11, 18), id="day"),
    pytest.param("week", _utc(2026, 11, 16), _utc(2026, 11, 23), id="week"),
    pytest.param("week", _utc(2026, 12, 28), _utc(2027, 1, 4), id="week-across-the-new-year"),
    pytest.param("month", _utc(2026, 1, 1), _utc(2026, 2, 1), id="month-of-31-days"),
    pytest.param("month", _utc(2026, 2, 1), _utc(2026, 3, 1), id="february-of-28-days"),
    pytest.param("month", _utc(2028, 2, 1), _utc(2028, 3, 1), id="february-of-29-days"),
    pytest.param("month", _utc(2026, 4, 1), _utc(2026, 5, 1), id="month-of-30-days"),
    pytest.param("month", _utc(2026, 12, 1), _utc(2027, 1, 1), id="december-into-january"),
]


@pytest.mark.parametrize(("window", "start", "end"), WINDOW_ENDS)
def test_u1_window_end(monkeypatch: pytest.MonkeyPatch, window: str, start: datetime, end: datetime) -> None:
    """The aware UTC start of the next window."""
    module = _pure(monkeypatch)
    found = module.window_end(window, int(start.timestamp()))
    assert found == end, f"window_end({window!r}, {start.isoformat()}): {found}, expected {end}"
    assert found.utcoffset() == timedelta(0), f"aware UTC: {found!r}"


# =============================================================================
# 3–6. COUNTING
# =============================================================================


@pytest.mark.asyncio
async def test_u1_the_first_call_inserts_the_row_with_every_count_one(monkeypatch: pytest.MonkeyPatch, private: Private) -> None:
    """No row → one row: every count 1, the five starts of ``now``, ``updated_at`` = ``now``; the call returns 1s."""
    module = _bound(monkeypatch, private)
    assert _row(private.path, "asset", "yfinance") is None, "setup: no row yet"

    result = await _call(module, "asset", "yfinance", NOW)

    assert result == _counts(module, 1, 1, 1, 1, 1), f"first call: {result}"
    row = _row(private.path, "asset", "yfinance")
    assert row is not None, "the first call must insert the row"
    assert _stored_counts(row) == (1, 1, 1, 1, 1), f"stored counts {_stored_counts(row)}"
    assert _stored_starts(row) == _expected_starts(NOW), f"stored starts {_stored_starts(row)}"
    assert row["updated_at"] == NOW, f"updated_at {row['updated_at']!r}, expected {NOW!r} (read back through the model's column)"


@pytest.mark.asyncio
async def test_u1_without_now_the_call_counts_at_the_current_utc_time(monkeypatch: pytest.MonkeyPatch, private: Private) -> None:
    """``now`` omitted: the windows are those of ``datetime.now(UTC)`` — the starts of an instant read just before or
    just after the call, ``updated_at`` between the two (a naive or local clock fails here off UTC)."""
    module = _bound(monkeypatch, private)
    before = datetime.now(UTC)
    result = await module.count_and_check("asset", "clock")
    after = datetime.now(UTC)

    assert result == _counts(module, 1, 1, 1, 1, 1), f"first call: {result}"
    row = _row(private.path, "asset", "clock")
    assert row is not None, "the call must insert the row"
    assert _stored_starts(row) in (_expected_starts(before), _expected_starts(after)), f"stored starts {_stored_starts(row)}, expected those of {before} or {after}"
    assert before <= row["updated_at"] <= after, f"updated_at {row['updated_at']!r} must lie between {before!r} and {after!r}"


@pytest.mark.asyncio
async def test_u1_calls_inside_the_same_windows_add_one_each(monkeypatch: pytest.MonkeyPatch, private: Private) -> None:
    """Three calls within the same minute: 1, 2, 3 in every window; ``updated_at`` the last call's ``now``."""
    module = _bound(monkeypatch, private)
    results = [await _call(module, "fx", "ECB", NOW + timedelta(seconds=offset)) for offset in (0, 10, 20)]

    assert results == [_counts(module, n, n, n, n, n) for n in (1, 2, 3)], f"results {results}"
    row = _row(private.path, "fx", "ECB")
    assert row is not None and _stored_counts(row) == (3, 3, 3, 3, 3), f"stored {row}"
    assert _stored_starts(row) == _expected_starts(NOW)
    assert row["updated_at"] == NOW + timedelta(seconds=20), f"updated_at {row['updated_at']!r}"


WINDOW_CHANGES = [
    pytest.param(NOW, _utc(2026, 11, 17, 13, 46, 10), (1, 2, 2, 2, 2), id="next-minute"),
    pytest.param(NOW, _utc(2026, 11, 17, 14, 0, 0), (1, 1, 2, 2, 2), id="next-hour"),
    pytest.param(NOW, _utc(2026, 11, 18, 0, 0, 0), (1, 1, 1, 2, 2), id="next-day"),
    pytest.param(_utc(2026, 11, 22, 23, 59, 59), _utc(2026, 11, 23, 0, 0, 0), (1, 1, 1, 1, 2), id="new-iso-week-sunday-to-monday-mid-month"),
    pytest.param(_utc(2026, 11, 30, 23, 59, 59), _utc(2026, 12, 1, 0, 0, 0), (1, 1, 1, 2, 1), id="new-month-monday-to-tuesday-mid-week"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("first", "second", "expected"), WINDOW_CHANGES)
async def test_u1_a_window_change_resets_exactly_its_windows(monkeypatch: pytest.MonkeyPatch, private: Private, first: datetime, second: datetime, expected: tuple[int, ...]) -> None:
    """One call, then one in a later window: the windows that changed restart at 1, the others count on; every start
    the second call's."""
    _weekday_barrier(_utc(2026, 11, 22), 6)
    _weekday_barrier(_utc(2026, 11, 30), 0)
    _weekday_barrier(_utc(2026, 12, 1), 1)
    module = _bound(monkeypatch, private)
    await _call(module, "asset", "justetf", first)

    result = await _call(module, "asset", "justetf", second)

    assert result == _counts(module, *expected), f"{first.isoformat()} then {second.isoformat()}: {result}, expected {expected}"
    row = _row(private.path, "asset", "justetf")
    assert row is not None and _stored_counts(row) == expected, f"stored {row}"
    assert _stored_starts(row) == _expected_starts(second), f"stored starts {_stored_starts(row)}, expected {_expected_starts(second)}"


@pytest.mark.asyncio
async def test_u1_a_clock_moved_back_never_lowers_a_start_and_counts_into_the_stored_window(monkeypatch: pytest.MonkeyPatch, private: Private) -> None:
    """A call at 13:45:30, then at 13:44:50, then at 12:59:59: every start stays at the first call's, every count 3."""
    module = _bound(monkeypatch, private)
    await _call(module, "asset", "yfinance", NOW)
    await _call(module, "asset", "yfinance", _utc(2026, 11, 17, 13, 44, 50))
    result = await _call(module, "asset", "yfinance", _utc(2026, 11, 17, 12, 59, 59))

    assert result == _counts(module, 3, 3, 3, 3, 3), f"counts {result}"
    row = _row(private.path, "asset", "yfinance")
    assert row is not None and _stored_starts(row) == _expected_starts(NOW), f"the starts must never go back: {row and _stored_starts(row)}"


# =============================================================================
# 7. LIMITS
# =============================================================================


@pytest.mark.asyncio
async def test_u1_a_full_minute_refuses_the_call_writes_nothing_and_admits_it_in_the_next_minute(monkeypatch: pytest.MonkeyPatch, private: Private) -> None:
    """``minute=3``: calls 1–3 pass; the 4th raises, the row unchanged (``updated_at`` too), ``resets_at`` 13:46:00,
    ``retry_after`` 30 s; at 13:46:00 the call passes, minute 1, hour 4."""
    module = _bound(monkeypatch, private)
    limits = module.CallLimits(minute=3)
    passed = [await _call(module, "asset", "yfinance", NOW + timedelta(seconds=offset), limits) for offset in (-20, -10, 0)]
    assert [result.minute for result in passed] == [1, 2, 3], f"calls 1–3 pass: {passed}"
    before = _row(private.path, "asset", "yfinance")

    error = await _refusal(module, "asset", "yfinance", NOW, limits)

    _assert_refusal(error, family="asset", plugin_code="yfinance", window="minute", limit=3, count=3, resets_at=_utc(2026, 11, 17, 13, 46), now=NOW)
    assert _row(private.path, "asset", "yfinance") == before, "a refused call is not counted: the row must be unchanged"

    admitted = await _call(module, "asset", "yfinance", _utc(2026, 11, 17, 13, 46), limits)
    assert admitted == _counts(module, 1, 4, 4, 4, 4), f"the rolled minute admits the call: {admitted}"


@pytest.mark.asyncio
async def test_u1_a_full_month_refuses_until_the_first_of_next_month(monkeypatch: pytest.MonkeyPatch, private: Private) -> None:
    """``month=2``: two calls on two days pass, the third raises naming the month, ``resets_at`` 1 December; on
    1 December the call passes, month 1."""
    module = _bound(monkeypatch, private)
    limits = module.CallLimits(month=2)
    await _call(module, "fx", "FED", _utc(2026, 11, 3, 8), limits)
    await _call(module, "fx", "FED", _utc(2026, 11, 10, 8), limits)
    before = _row(private.path, "fx", "FED")

    error = await _refusal(module, "fx", "FED", NOW, limits)

    _assert_refusal(error, family="fx", plugin_code="FED", window="month", limit=2, count=2, resets_at=_utc(2026, 12, 1), now=NOW)
    assert _row(private.path, "fx", "FED") == before, "the row must be unchanged"
    admitted = await _call(module, "fx", "FED", _utc(2026, 12, 1), limits)
    assert admitted.month == 1, f"the new month admits the call: {admitted}"


SEVERAL_FULL = [
    pytest.param({"minute": 2, "hour": 2}, "hour", 2, _utc(2026, 11, 17, 14), id="minute-and-hour-full-names-the-hour"),
    pytest.param({"minute": 2, "hour": 2, "month": 2}, "month", 2, _utc(2026, 12, 1), id="minute-hour-month-full-names-the-month"),
    pytest.param({"minute": 2, "day": 2, "week": 2}, "week", 2, _utc(2026, 11, 23), id="minute-day-week-full-names-the-week"),
    pytest.param({"minute": 2, "hour": 5, "month": 9}, "minute", 2, _utc(2026, 11, 17, 13, 46), id="only-the-minute-full-names-the-minute"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("limits", "window", "limit", "resets_at"), SEVERAL_FULL)
async def test_u1_several_full_windows_name_the_one_ending_last(monkeypatch: pytest.MonkeyPatch, private: Private, limits: dict[str, int], window: str, limit: int, resets_at: datetime) -> None:
    """Two calls fill every window limited to 2; the third is refused naming, of the full windows, the one ending last
    (retrying before it ends is useless)."""
    module = _bound(monkeypatch, private)
    call_limits = module.CallLimits(**limits)
    await _call(module, "asset", "borsa_italiana", NOW - timedelta(seconds=5), call_limits)
    await _call(module, "asset", "borsa_italiana", NOW - timedelta(seconds=1), call_limits)
    before = _row(private.path, "asset", "borsa_italiana")

    error = await _refusal(module, "asset", "borsa_italiana", NOW, call_limits)

    _assert_refusal(error, family="asset", plugin_code="borsa_italiana", window=window, limit=limit, count=2, resets_at=resets_at, now=NOW)
    assert _row(private.path, "asset", "borsa_italiana") == before, "the row must be unchanged"


# =============================================================================
# 8. LIMIT 0 — THE PLUGIN STOPPED
# =============================================================================


@pytest.mark.asyncio
async def test_u1_a_limit_of_zero_refuses_without_creating_a_row(monkeypatch: pytest.MonkeyPatch, private: Private) -> None:
    """``day=0`` and no row: refused naming the day, count 0, ``resets_at`` tomorrow; the table still empty."""
    module = _bound(monkeypatch, private)

    error = await _refusal(module, "asset", "css_scraper", NOW, module.CallLimits(day=0))

    _assert_refusal(error, family="asset", plugin_code="css_scraper", window="day", limit=0, count=0, resets_at=_utc(2026, 11, 18), now=NOW)
    assert _row_count(private.path) == 0, "a stopped plugin's call must not create a row"


@pytest.mark.asyncio
async def test_u1_a_limit_of_zero_names_the_longest_stopped_window(monkeypatch: pytest.MonkeyPatch, private: Private) -> None:
    """``minute=0, week=0`` (and a positive hour): refused naming the week, the zero window ending last."""
    module = _bound(monkeypatch, private)

    error = await _refusal(module, "fx", "BOE", NOW, module.CallLimits(minute=0, hour=100, week=0))

    _assert_refusal(error, family="fx", plugin_code="BOE", window="week", limit=0, count=0, resets_at=_utc(2026, 11, 23), now=NOW)
    assert _row_count(private.path) == 0, "no row created"


@pytest.mark.asyncio
async def test_u1_a_limit_of_zero_leaves_an_existing_row_unchanged(monkeypatch: pytest.MonkeyPatch, private: Private) -> None:
    """One counted call, then ``hour=0``: refused naming the hour, the row unchanged; the count is the hour's current
    count (1) or 0 — the contract allows either."""
    module = _bound(monkeypatch, private)
    await _call(module, "asset", "yfinance", NOW - timedelta(seconds=10))
    before = _row(private.path, "asset", "yfinance")

    error = await _refusal(module, "asset", "yfinance", NOW, module.CallLimits(hour=0))

    _assert_refusal(error, family="asset", plugin_code="yfinance", window="hour", limit=0, count={0, 1}, resets_at=_utc(2026, 11, 17, 14), now=NOW)
    assert _row(private.path, "asset", "yfinance") == before, "the row must be unchanged"


# =============================================================================
# 9–10. NO LIMITS; INDEPENDENT ROWS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("no_limits", ["none", "all-none"])
async def test_u1_without_limits_a_call_is_never_refused(monkeypatch: pytest.MonkeyPatch, private: Private, no_limits: str) -> None:
    """``limits=None`` or ``CallLimits()``: five calls in one minute all pass, every count 5."""
    module = _bound(monkeypatch, private)
    limits = None if no_limits == "none" else module.CallLimits()
    results = [await _call(module, "asset", "yfinance", NOW, limits) for _ in range(5)]
    assert results[-1] == _counts(module, 5, 5, 5, 5, 5), f"results {results}"


@pytest.mark.asyncio
async def test_u1_rows_of_different_pairs_are_independent_and_group_is_a_family_like_any(monkeypatch: pytest.MonkeyPatch, private: Private) -> None:
    """(asset, alpha) ×1, (asset, beta) ×2, (fx, alpha) ×3, (group, alpha) ×4: four rows, each its own counts; a full
    minute on (asset, alpha) refuses only that pair."""
    module = _bound(monkeypatch, private)
    pairs = {("asset", "alpha"): 1, ("asset", "beta"): 2, ("fx", "alpha"): 3, ("group", "alpha"): 4}
    for (family, code), calls in pairs.items():
        for _ in range(calls):
            await _call(module, family, code, NOW)
    found = {pair: _stored_counts(_row(private.path, *pair) or {f"{w}_count": None for w in WINDOWS}) for pair in pairs}
    assert found == {pair: (calls,) * 5 for pair, calls in pairs.items()}, f"each pair its own counts: {found}"
    assert _row_count(private.path) == 4, "one row per pair"

    one = module.CallLimits(minute=1)
    await _refusal(module, "asset", "alpha", NOW, one)
    admitted = await _call(module, "asset", "gamma", NOW, one)
    assert admitted == _counts(module, 1, 1, 1, 1, 1), f"another pair is not limited by (asset, alpha): {admitted}"


# =============================================================================
# 11. TWO PROCESSES ON ONE FILE
# =============================================================================

CHILD_SCRIPT = '''
"""A child of test_call_counter: counts one row of a private SQLite file, after a go line on stdin."""
import asyncio
import dataclasses
import json
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.db import session  # the production PRAGMA listener: WAL, busy_timeout
from backend.app.services.platform import call_counter


def _tripwire(*_args, **_kwargs):
    raise AssertionError("child: the lane engine was asked for")


async def main(db, family, code, calls, now, minute_limit, out):
    session.get_async_engine = _tripwire
    session.get_sync_engine = _tripwire
    engine = create_async_engine(f"sqlite+aiosqlite:///{db}", poolclass=NullPool)
    call_counter.get_async_engine = lambda: engine
    limits = call_counter.CallLimits(minute=int(minute_limit)) if minute_limit != "none" else None
    when = datetime.fromisoformat(now)
    print("ready", flush=True)
    sys.stdin.readline()
    results = []
    try:
        for _ in range(int(calls)):
            try:
                counts = await call_counter.count_and_check(family, code, limits, now=when)
                results.append(None if counts is None else dataclasses.asdict(counts))
            except call_counter.CallLimitReached as refused:
                results.append({"refused": refused.window, "count": refused.count})
    finally:
        await engine.dispose()
    Path(out).write_text(json.dumps(results))


asyncio.run(main(*sys.argv[1:]))
'''


def _two_children(tmp_path: Path, db: Path, calls: int, minute_limit: Optional[int]) -> list[list[Any]]:
    """Two child processes counting (``asset``, ``race``) on ``db`` at the same ``now``, started together: each prints
    ``ready`` after its imports, and both get their ``go`` only when both are ready."""
    script = tmp_path / "count_child.py"
    script.write_text(CHILD_SCRIPT)
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(PROJECT_ROOT), env.get("PYTHONPATH")]))
    env["LIBREFOLIO_TEST_MODE"] = "1"
    env["TMPDIR"] = env.get("TMPDIR") or str(tmp_path)
    outs = [tmp_path / f"child-{index}.json" for index in range(2)]
    children = [
        subprocess.Popen(
            [sys.executable, str(script), str(db), "asset", "race", str(calls), NOW.isoformat(), "none" if minute_limit is None else str(minute_limit), str(out)],
            cwd=PROJECT_ROOT,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for out in outs
    ]
    try:
        for child in children:
            seen = []
            while (line := child.stdout.readline()) and line.strip() != "ready":
                seen.append(line)
            assert line.strip() == "ready", f"setup: a child died before its barrier: {''.join(seen)} {child.stderr.read()}"
        for child in children:
            child.stdin.write("go\n")
            child.stdin.flush()
        for child in children:
            _stdout, stderr = child.communicate(timeout=180)
            assert child.returncode == 0, f"a child failed ({child.returncode}): {stderr}"
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
                child.wait()
    return [json.loads(out.read_text()) for out in outs]


def _two_process_setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Barriers in this process first: the module and the table exist; then a new private file for the children."""
    _pure(monkeypatch)
    db = tmp_path / "race.db"
    _build_by_models(db)
    _table_barrier(db)
    return db


def test_u1_two_processes_counting_one_row_lose_no_update(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """2 × 50 calls at once, no limit: the row ends at 100 in every window, and the minute counts the calls returned
    are exactly 1..100, each once — two calls never read the same count."""
    db = _two_process_setup(tmp_path, monkeypatch)

    results = _two_children(tmp_path, db, 50, None)

    returned = [result["minute"] for child in results for result in child if result is not None]
    assert len(returned) == 100, f"every call returns its counts (None = a database failure): {[len(child) for child in results]} calls, {sum(r is None for c in results for r in c)} None"
    assert sorted(returned) == list(range(1, 101)), f"each count once: duplicates {sorted({n for n in returned if returned.count(n) > 1})}"
    row = _row(db, "asset", "race")
    assert row is not None and _stored_counts(row) == (100,) * 5, f"stored {row}"


def test_u1_two_processes_against_a_limit_admit_exactly_the_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """2 × 50 calls at once against ``minute=60``, all in one minute: exactly 60 pass across both (counts 1..60, each
    once), 40 refused naming the minute; the row at 60."""
    db = _two_process_setup(tmp_path, monkeypatch)

    results = _two_children(tmp_path, db, 50, 60)

    flat = [result for child in results for result in child]
    assert None not in flat, f"no call may hit a database failure: {flat.count(None)} None"
    passed = sorted(result["minute"] for result in flat if "refused" not in result)
    refused = [result for result in flat if "refused" in result]
    assert passed == list(range(1, 61)), f"exactly 60 pass, each count once: {len(passed)} passed, {passed[:5]}…{passed[-5:]}"
    assert len(refused) == 40 and {result["refused"] for result in refused} == {"minute"}, f"40 refused naming the minute: {len(refused)}, {({r['refused'] for r in refused})}"
    assert {result["count"] for result in refused} == {60}, f"a refusal reports the full count: {({r['count'] for r in refused})}"
    row = _row(db, "asset", "race")
    assert row is not None and _stored_counts(row) == (60,) * 5, f"stored {row}"


# =============================================================================
# 12. THE DATABASE FAILING
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["file-in-a-missing-folder", "table-missing"])
async def test_u1_a_database_failure_lets_the_call_go_with_one_warning(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, failure: str) -> None:
    """The engine on a file in a folder that does not exist, or on a database without the table: ``count_and_check``
    returns None, raises nothing, and logs one warning naming the family and the plugin."""
    module = _counter_module()
    path = tmp_path / "missing-folder" / "counters.db" if failure == "file-in-a-missing-folder" else tmp_path / "empty.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}", poolclass=NullPool)
    monkeypatch.setattr(module, "get_async_engine", lambda: engine, raising=True)
    family, code = "asset", f"u1_failing_{failure.replace('-', '_')}"
    try:
        with _captured(module) as events:
            result = await module.count_and_check(family, code, module.CallLimits(minute=5), now=NOW)
    finally:
        await engine.dispose()

    assert result is None, f"a database failure lets the call go, returning None: {result}"
    warnings = [event for event in events if event.get("log_level") == "warning"]
    assert len(warnings) == 1, f"one warning: {warnings}"
    assert family in repr(warnings[0]) and code in repr(warnings[0]), f"the warning must name {family} and {code}: {warnings[0]}"


@pytest.mark.asyncio
async def test_u1_a_stopped_plugin_stays_stopped_when_the_database_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Review: limit 0 stops the plugin whatever the database does. With the engine on a file in a missing folder, a
    stopped window still raises ``CallLimitReached`` (count 0: nothing could be read), never None, which would let the
    call go."""
    module = _counter_module()
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'missing-folder' / 'counters.db'}", poolclass=NullPool)
    monkeypatch.setattr(module, "get_async_engine", lambda: engine, raising=True)
    try:
        with pytest.raises(module.CallLimitReached) as raised:
            await module.count_and_check("asset", "u1_stopped_broken", module.CallLimits(minute=0), now=NOW)
    finally:
        await engine.dispose()
    assert (raised.value.window, raised.value.limit, raised.value.count) == ("minute", 0, 0)


@pytest.mark.asyncio
async def test_u1_a_write_lock_held_past_the_busy_timeout_lets_the_call_go(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Review: the plan's own failure, the file's write lock held by another connection beyond the counter's own wait
    (2 s since U2): the call goes (None) with one warning, nothing raised, and the row is not touched."""
    module = _counter_module()
    path = tmp_path / "locked.db"
    setup = create_async_engine(f"sqlite+aiosqlite:///{path}", poolclass=NullPool)
    async with setup.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)
    await setup.dispose()
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}", poolclass=NullPool)

    monkeypatch.setattr(module, "get_async_engine", lambda: engine, raising=True)
    holder = sqlite3.connect(path, isolation_level=None)
    try:
        holder.execute("BEGIN IMMEDIATE")
        with _captured(module) as events:
            result = await module.count_and_check("asset", "u1_locked", module.CallLimits(minute=5), now=NOW)
    finally:
        holder.execute("ROLLBACK")
        holder.close()
        await engine.dispose()
    assert result is None, f"a lock past the timeout lets the call go: {result}"
    assert len([event for event in events if event.get("log_level") == "warning"]) == 1, events
    assert _row(path, "asset", "u1_locked") is None


# =============================================================================
# 13. READING FOR THE SETTINGS PAGE
# =============================================================================


@pytest.mark.asyncio
async def test_u1_read_counts_of_a_pair_without_a_row_is_all_zeros_and_writes_nothing(monkeypatch: pytest.MonkeyPatch, private: Private) -> None:
    module = _bound(monkeypatch, private)

    result = await module.read_counts("asset", "never_called", now=NOW)

    assert result == _counts(module, 0, 0, 0, 0, 0), f"no row reads as zeros: {result}"
    assert _row_count(private.path) == 0, "reading must not create a row"


READS = [
    pytest.param(NOW + timedelta(seconds=5), (2, 2, 2, 2, 2), id="same-minute"),
    pytest.param(_utc(2026, 11, 17, 13, 50), (0, 2, 2, 2, 2), id="minute-rolled"),
    pytest.param(_utc(2026, 11, 17, 14, 0, 10), (0, 0, 2, 2, 2), id="minute-and-hour-rolled"),
    pytest.param(_utc(2026, 11, 22, 9), (0, 0, 0, 2, 2), id="day-rolled-same-week"),
    pytest.param(_utc(2026, 11, 23, 9), (0, 0, 0, 0, 2), id="new-week-same-month"),
    pytest.param(_utc(2026, 12, 1, 9), (0, 0, 0, 0, 0), id="new-month"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("when", "expected"), READS)
async def test_u1_read_counts_reads_stale_windows_as_zero_and_never_writes(monkeypatch: pytest.MonkeyPatch, private: Private, when: datetime, expected: tuple[int, ...]) -> None:
    """Two calls at 13:45, read later: a window whose start is older than the current window's reads 0, the others as
    stored; the row unchanged, ``updated_at`` included."""
    module = _bound(monkeypatch, private)
    await _call(module, "fx", "SNB", NOW - timedelta(seconds=10))
    await _call(module, "fx", "SNB", NOW)
    before = _row(private.path, "fx", "SNB")

    result = await module.read_counts("fx", "SNB", now=when)

    assert result == _counts(module, *expected), f"read at {when.isoformat()}: {result}, expected {expected}"
    assert _row(private.path, "fx", "SNB") == before, "reading must never write"


# =============================================================================
# 14. U2 — THE COUNTER'S OWN BUSY TIMEOUT
# =============================================================================


async def _built(path: Path) -> None:
    setup = create_async_engine(f"sqlite+aiosqlite:///{path}", poolclass=NullPool)
    try:
        async with setup.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
    finally:
        await setup.dispose()


async def _busy_timeout(engine: AsyncEngine) -> int:
    async with engine.connect() as connection:
        return (await connection.exec_driver_sql("PRAGMA busy_timeout")).scalar_one()


async def _timed_under_a_held_lock(module: ModuleType, path: Path, code: str) -> tuple[Any, float]:
    """``count_and_check`` while another connection holds ``BEGIN IMMEDIATE`` on the file: its result and seconds."""
    holder = sqlite3.connect(path, isolation_level=None)
    try:
        holder.execute("BEGIN IMMEDIATE")
        started = time.monotonic()
        result = await module.count_and_check("asset", code, module.CallLimits(minute=5), now=NOW)
        return result, time.monotonic() - started
    finally:
        holder.execute("ROLLBACK")
        holder.close()


def test_u2_the_counter_names_its_busy_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """U2 8: ``COUNTER_BUSY_TIMEOUT_MS == 2000``, the counter's own wait for the file's write lock."""
    assert getattr(_pure(monkeypatch), "COUNTER_BUSY_TIMEOUT_MS", None) == 2000


@pytest.mark.asyncio
async def test_u2_a_held_write_lock_lets_the_call_go_after_the_counters_two_seconds(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """U2 8a: a plain engine (the session listener's 30 000 ms on every connection, checked): another connection holding
    ``BEGIN IMMEDIATE`` makes ``count_and_check`` return None after the counter's own ~2 s, not 30; nothing written.
    Red on HEAD after the full 30 s."""
    module = _counter_module()
    path = tmp_path / "busy.db"
    await _built(path)
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}", poolclass=NullPool)
    monkeypatch.setattr(module, "get_async_engine", lambda: engine, raising=True)
    try:
        assert await _busy_timeout(engine) == 30000, "barrier: the plain engine carries the session listener's 30 000 ms"
        with _captured(module):
            result, elapsed = await _timed_under_a_held_lock(module, path, "u2_busy_plain")
    finally:
        await engine.dispose()

    assert result is None, f"a lock held past the counter's timeout lets the call go: {result}"
    assert 1.5 <= elapsed < 10, f"the counter waits its own ~2 s, not the session's 30: {elapsed:.2f} s"
    assert _row(path, "asset", "u2_busy_plain") is None


@pytest.mark.asyncio
async def test_u2_the_counter_restores_the_connections_busy_timeout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """U2 8b: one pooled connection (pool of one, no overflow) serves every use: after a counted call, a refused one and
    one that timed out on a held lock (in ~2 s), the same connection reads ``busy_timeout`` 30 000 again."""
    module = _counter_module()
    path = tmp_path / "pooled.db"
    await _built(path)
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}", poolclass=AsyncAdaptedQueuePool, pool_size=1, max_overflow=0)
    checked_out: list[int] = []
    event.listen(engine.sync_engine, "checkout", lambda dbapi_connection, _record, _proxy: checked_out.append(id(dbapi_connection)))
    monkeypatch.setattr(module, "get_async_engine", lambda: engine, raising=True)
    try:
        assert await _busy_timeout(engine) == 30000, "barrier: the session listener's 30 000 ms"
        assert await module.count_and_check("asset", "u2_busy_pooled", module.CallLimits(minute=1), now=NOW) == _counts(module, 1, 1, 1, 1, 1)
        after_counted = await _busy_timeout(engine)
        with pytest.raises(module.CallLimitReached):
            await module.count_and_check("asset", "u2_busy_pooled", module.CallLimits(minute=1), now=NOW)
        after_refused = await _busy_timeout(engine)
        with _captured(module):
            result, elapsed = await _timed_under_a_held_lock(module, path, "u2_busy_pooled_locked")
        after_locked = await _busy_timeout(engine)
    finally:
        await engine.dispose()

    assert result is None
    assert 1.5 <= elapsed < 10, f"the counter waits its own ~2 s on the pooled connection too: {elapsed:.2f} s"
    assert (after_counted, after_refused, after_locked) == (30000, 30000, 30000), "the connection's own value is restored after each counter transaction"
    assert len(set(checked_out)) == 1 and len(checked_out) >= 7, f"barrier: one connection served every use: {checked_out}"


@pytest.mark.asyncio
async def test_u2_a_count_cancelled_while_it_waits_never_returns_the_short_wait_to_the_pool(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Review: a count cancelled while it waits for a held lock (a closed search stream, an outer ``wait_for``) leaves no
    connection in the pool with the counter's 2 s: the pooled connection reads 30 000 again, or was replaced."""
    module = _counter_module()
    path = tmp_path / "cancelled.db"
    await _built(path)
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}", poolclass=AsyncAdaptedQueuePool, pool_size=1, max_overflow=0)
    monkeypatch.setattr(module, "get_async_engine", lambda: engine, raising=True)
    holder = sqlite3.connect(path, isolation_level=None)
    try:
        holder.execute("BEGIN IMMEDIATE")
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(module.count_and_check("asset", "u2_cancelled", module.CallLimits(minute=5), now=NOW), timeout=0.3)
        holder.execute("ROLLBACK")
        after = await _busy_timeout(engine)
    finally:
        holder.close()
        await engine.dispose()
    assert after == 30000, f"the pool hands out a connection with the app's wait, not the counter's: {after}"


# =============================================================================
# 15. U2 — THE FAILURE WARNING, AT MOST ONCE A MINUTE PER PAIR
# =============================================================================


class _Monotonic:
    """``call_counter._monotonic`` in the tests: moves only when the test moves it."""

    def __init__(self) -> None:
        self.now = 5_000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture(autouse=True)
def forget_failure_warnings() -> Iterator[None]:
    """The counter's memory of the warnings it wrote (``_warned_at``, a dict) is empty before and after each test; HEAD
    has none."""

    def clear() -> None:
        module = sys.modules.get(MODULE)
        memory = getattr(module, "_warned_at", None) if module is not None else None
        if isinstance(memory, dict):
            memory.clear()

    clear()
    yield
    clear()


def _warned_pairs(events: list[dict[str, Any]], codes: tuple[str, ...]) -> list[str]:
    """The codes named by each warning, in order."""
    return [next((code for code in codes if code in repr(event)), "<none>") for event in events if event.get("log_level") == "warning"]


@pytest_asyncio.fixture
async def broken(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[_Monotonic]:
    """The counter on a file in a missing folder (every statement fails), its warning clock a fake one."""
    module = _counter_module()
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'missing-folder' / 'counters.db'}", poolclass=NullPool)
    monkeypatch.setattr(module, "get_async_engine", lambda: engine, raising=True)
    clock = _Monotonic()
    monkeypatch.setattr(module, "_monotonic", clock, raising=False)  # red on HEAD as «too many warnings», not here
    try:
        yield clock
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_u2_a_failing_pair_warns_once_a_minute_and_another_pair_warns_its_own(broken: _Monotonic) -> None:
    """U2 9: pair A fails twice within 60 s → one warning; pair B fails → its own warning. Every call still goes (None)."""
    module = _counter_module()
    codes = ("u2_warn_a", "u2_warn_b")
    with _captured(module) as events:
        first = await module.count_and_check("asset", codes[0], module.CallLimits(minute=5), now=NOW)
        broken.now += 30
        second = await module.count_and_check("asset", codes[0], module.CallLimits(minute=5), now=NOW)
        other = await module.count_and_check("asset", codes[1], module.CallLimits(minute=5), now=NOW)

    assert (first, second, other) == (None, None, None)
    assert _warned_pairs(events, codes) == ["u2_warn_a", "u2_warn_b"]


@pytest.mark.asyncio
async def test_u2_a_failing_pair_warns_again_after_a_minute(broken: _Monotonic) -> None:
    """U2 9: A fails at t, t+30 s (silent) and t+61 s (warned again): two warnings."""
    module = _counter_module()
    with _captured(module) as events:
        for step in (0, 30, 31):
            broken.now += step
            assert await module.count_and_check("asset", "u2_warn_again", None, now=NOW) is None

    assert _warned_pairs(events, ("u2_warn_again",)) == ["u2_warn_again", "u2_warn_again"]


@pytest.mark.asyncio
async def test_u2_a_stopped_plugin_on_a_failing_database_warns_once_a_minute(broken: _Monotonic) -> None:
    """U2 9: the limit-0 path's own warning follows the same rule: two refusals within 60 s on a failing database, one
    warning; both still refused."""
    module = _counter_module()
    with _captured(module) as events:
        for step in (0, 20):
            broken.now += step
            with pytest.raises(module.CallLimitReached):
                await module.count_and_check("asset", "u2_warn_stopped", module.CallLimits(minute=0), now=NOW)

    assert _warned_pairs(events, ("u2_warn_stopped",)) == ["u2_warn_stopped"]
