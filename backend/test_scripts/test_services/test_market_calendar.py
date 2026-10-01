"""Market-closed repeats: the holiday table and the process that builds it.

Developer's decision of 30/09/2026. Some price sources (justETF) store a row for every calendar day:
a weekend or an exchange holiday repeats the last close. The risk engine reads such a row as a
carry, not a quote. What tells a weekday holiday apart is the union of the weekday holidays of seven
exchange calendars from QuantLib — TARGET, Borsa Italiana, Xetra, Euronext Paris, London, SIX and
NYSE — over 1970–2100. The union is safe because the rule also requires an exact repeat of the row
before.

QuantLib never enters the web process
(`LibreFolio_devWiki/wiki/decisions/risk-quant-engine-process-boundary.md`), so the table is built
in a separate `spawn` process at every startup: in the background from the app lifespan, awaited by
the first computation that needs it, shared by concurrent callers, and given up — weekends still
apply — when the build fails, until a retry delay has passed.

The module is imported inside each test on purpose: until it exists every test fails on its own, at
run time, instead of breaking the collection of the whole risk suite that runs this file.

The build process is replaced through the documented seam `_build_in_subprocess(first_year,
last_year)` everywhere except in two tests that start it for real: one stops it mid-build and checks
that nothing survives, the other runs it in a fresh interpreter and checks that interpreter never
imported QuantLib. Every other test resets the module around itself — shutdown, then reload — so no
build, cached table or child process outlives it.
"""

from __future__ import annotations

import asyncio
import importlib
import json
import logging
import os
import subprocess
import sys
import textwrap
import time
from collections.abc import Awaitable, Callable
from datetime import date
from decimal import Decimal
from multiprocessing import resource_tracker
from pathlib import Path
from types import SimpleNamespace

import psutil
import pytest
import pytest_asyncio
import QuantLib as ql
from structlog.testing import capture_logs

MODULE = "backend.app.services.market_calendar"
REPO_ROOT = Path(__file__).resolve().parents[3]


def market_calendar():
    """The module under test, imported at run time (see the module docstring)."""
    return importlib.import_module(MODULE)


async def _reset_market_calendar() -> None:
    """Stop whatever the module is doing and give it back its import-time state.

    Reloading keeps the module object — and the functions other modules imported from it — while
    re-running its body, so every cached table, build and flag starts over.
    """
    try:
        module = importlib.import_module(MODULE)
    except ImportError:
        return
    shutdown = getattr(module, "shutdown_market_holidays", None)
    if shutdown is not None:
        await asyncio.wait_for(shutdown(), timeout=30)
    importlib.reload(module)


@pytest_asyncio.fixture
async def fresh_calendar():
    """No cached table, no build in progress, no child process — before the test and after it."""
    await _reset_market_calendar()
    yield
    await _reset_market_calendar()


async def _until(predicate: Callable[[], object], message: str | Callable[[], str], timeout: float = 10.0) -> None:
    """Poll a condition with a deadline; the event loop keeps running while it waits."""
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > deadline:
            raise AssertionError(message() if callable(message) else message)
        await asyncio.sleep(0.005)


async def _call_until(call: Callable[[], Awaitable[object]], expected: object, timeout: float = 5.0) -> object:
    """Call again until the answer is `expected` or the deadline passes; return the last answer."""
    deadline = time.monotonic() + timeout
    while True:
        answer = await asyncio.wait_for(call(), timeout=timeout)
        if answer == expected or time.monotonic() > deadline:
            return answer
        await asyncio.sleep(0.01)


async def _cancel(*tasks: object) -> None:
    """Cancel what a test started and wait for it, so no task outlives the test's event loop."""
    pending = [task for task in tasks if isinstance(task, asyncio.Future) and not task.done()]
    for task in pending:
        task.cancel()
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)


class BuildSeam:
    """Stands in for `_build_in_subprocess(first_year, last_year)` and counts the builds it runs.

    Each build waits for `release` (already set unless told otherwise), then returns the next
    outcome — a list of ISO dates — or raises it when it is an exception. The last outcome repeats.
    """

    def __init__(self, *outcomes: list[str] | BaseException, released: bool = True) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[tuple[int, int]] = []
        self.release = asyncio.Event()
        if released:
            self.release.set()

    async def build(self, first_year: int, last_year: int) -> list[str]:
        self.calls.append((first_year, last_year))
        outcome = self.outcomes[min(len(self.calls), len(self.outcomes)) - 1]
        await self.release.wait()
        if isinstance(outcome, BaseException):
            raise outcome
        return list(outcome)


# Unsorted on purpose: the table is a set of dates, whatever order the build reports them in.
BUILT = ["2025-12-25", "2025-04-18"]
BUILT_DAYS = frozenset({date(2025, 4, 18), date(2025, 12, 25)})


# ---------------------------------------------------------------------------
# The table: a pure function of QuantLib, run here in the test process
# ---------------------------------------------------------------------------


def _quantlib_weekday_union(first_year: int, last_year: int) -> list[str]:
    """The definition written out: every weekday holiday of the seven calendars, once, in order."""
    calendars = (
        ql.TARGET(),
        ql.Italy(ql.Italy.Exchange),  # Borsa Italiana
        ql.Germany(ql.Germany.Xetra),
        ql.France(ql.France.Exchange),  # Euronext Paris
        ql.UnitedKingdom(ql.UnitedKingdom.Exchange),  # London
        ql.Switzerland(),  # SIX
        ql.UnitedStates(ql.UnitedStates.NYSE),
    )
    first, last = ql.Date(1, 1, first_year), ql.Date(31, 12, last_year)
    return sorted({date(day.year(), day.month(), day.dayOfMonth()).isoformat() for calendar in calendars for day in calendar.holidayList(first, last, False)})


def test_the_table_spans_1970_to_2100():
    assert market_calendar().MARKET_HOLIDAY_YEARS == (1970, 2100)


def test_the_table_is_the_weekday_union_of_the_seven_exchange_calendars():
    table = market_calendar().build_market_holidays(1970, 2100)

    assert isinstance(table, list)
    assert all(isinstance(item, str) for item in table)
    assert table == sorted(set(table)), "sorted ISO dates, each once"
    days = [date.fromisoformat(item) for item in table]
    # A weekend is closed anyway: the table holds the weekdays the rule could not tell apart alone.
    assert all(day.weekday() < 5 for day in days)
    assert (days[0].year, days[-1].year) == (1970, 2100)
    assert table == _quantlib_weekday_union(1970, 2100)


# Checked against QuantLib 1.43 before being pinned. Xetra is open on New Year's Eve in that
# version: 31 December comes from Borsa Italiana and Euronext Paris.
KNOWN_2025_HOLIDAYS = [
    pytest.param("2025-04-18", id="good-friday-every-exchange"),
    pytest.param("2025-04-21", id="easter-monday-europe-and-london"),
    pytest.param("2025-05-01", id="labour-day-target"),
    pytest.param("2025-08-15", id="assumption-borsa-italiana-only"),
    pytest.param("2025-12-24", id="christmas-eve-xetra-borsa-italiana-euronext"),
    pytest.param("2025-12-31", id="new-years-eve-borsa-italiana-euronext"),
    pytest.param("2025-12-25", id="christmas"),
    pytest.param("2025-12-26", id="boxing-day"),
    pytest.param("2025-07-04", id="independence-day-nyse-only"),
    pytest.param("2025-11-27", id="thanksgiving-nyse-only"),
    pytest.param("2025-05-26", id="spring-bank-holiday-london-and-memorial-day-nyse"),
    pytest.param("2025-08-25", id="summer-bank-holiday-london-only"),
    pytest.param("2025-05-29", id="ascension-six-only"),
    pytest.param("2025-08-01", id="swiss-national-day-six-only-a-friday"),
    pytest.param("2025-01-09", id="nyse-special-closure-national-day-of-mourning"),
]


@pytest.mark.parametrize("holiday", KNOWN_2025_HOLIDAYS)
def test_a_known_exchange_holiday_of_2025_is_in_the_table(holiday):
    assert holiday in market_calendar().build_market_holidays(2025, 2025)


def test_an_ordinary_trading_day_and_a_weekend_holiday_are_not_in_the_table():
    module = market_calendar()

    assert "2025-03-12" not in module.build_market_holidays(2025, 2025)
    # Christmas 2021 fell on a weekend: the table holds the weekdays the exchanges closed instead —
    # NYSE's observed Christmas and Christmas Eve on the 24th, London's substitutes on the 27th and
    # 28th, New Year's Eve on the 31st — and neither weekend day.
    december_2021 = [item for item in module.build_market_holidays(2021, 2021) if item.startswith("2021-12-")]
    assert december_2021 == ["2021-12-24", "2021-12-27", "2021-12-28", "2021-12-31"]


# ---------------------------------------------------------------------------
# The rule: a carry is an exact repeat of the row before, on a weekend or a market holiday
# ---------------------------------------------------------------------------

SATURDAY = date(2025, 3, 8)
SUNDAY = date(2025, 3, 9)
WEDNESDAY = date(2025, 3, 12)
GOOD_FRIDAY = date(2025, 4, 18)
CLOSED = frozenset({GOOD_FRIDAY})


@pytest.mark.parametrize(
    ("day", "close", "previous_close", "expected"),
    [
        pytest.param(SATURDAY, "101.5", "101.5", True, id="weekend-repeat-is-a-carry"),
        pytest.param(SUNDAY, "101.5", "101.5", True, id="sunday-repeat-is-a-carry"),
        pytest.param(SATURDAY, "101.75", "101.5", False, id="weekend-move-is-a-quote"),
        pytest.param(WEDNESDAY, "101.5", "101.5", False, id="flat-weekday-is-a-quote"),
        pytest.param(GOOD_FRIDAY, "101.5", "101.5", True, id="holiday-repeat-is-a-carry"),
        pytest.param(GOOD_FRIDAY, "101.75", "101.5", False, id="holiday-move-is-a-quote"),
        pytest.param(SATURDAY, "101.5", None, False, id="first-row-on-a-weekend-is-a-quote"),
        pytest.param(GOOD_FRIDAY, "101.5", None, False, id="first-row-on-a-holiday-is-a-quote"),
        pytest.param(SATURDAY, "101.500001", "101.5", False, id="exact-repeats-only-no-tolerance"),
        pytest.param(SATURDAY, "101.50", "101.5", True, id="the-same-decimal-at-another-scale-repeats"),
    ],
)
def test_a_carry_is_an_exact_repeat_on_a_weekend_or_a_market_holiday(day, close, previous_close, expected):
    previous = Decimal(previous_close) if previous_close is not None else None

    assert market_calendar().is_market_closed_repeat(day, Decimal(close), previous, CLOSED) is expected


# ---------------------------------------------------------------------------
# One build, shared, reused, retried — through the `_build_in_subprocess` seam
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_concurrent_callers_share_one_build_and_later_calls_reuse_it(fresh_calendar, monkeypatch):
    module = market_calendar()
    seam = BuildSeam(BUILT, released=False)
    monkeypatch.setattr(module, "_build_in_subprocess", seam.build)

    first = asyncio.create_task(module.ensure_market_holidays())
    second = asyncio.create_task(module.ensure_market_holidays())
    try:
        await _until(lambda: seam.calls, "neither caller started the build")
        for _ in range(10):  # let the second caller reach its wait as well
            await asyncio.sleep(0)
        assert not first.done() and not second.done(), "a caller answered before the build finished"
        seam.release.set()
        results = await asyncio.wait_for(asyncio.gather(first, second), timeout=5)
    finally:
        await _cancel(first, second)

    assert results == [BUILT_DAYS, BUILT_DAYS]
    assert all(isinstance(result, frozenset) for result in results)
    # One build for both callers, over the whole span of the table.
    assert seam.calls == [(1970, 2100)]

    # Once built, the table is served without building again.
    assert await asyncio.wait_for(module.ensure_market_holidays(), timeout=5) == BUILT_DAYS
    assert len(seam.calls) == 1


@pytest.mark.asyncio
async def test_a_cancelled_caller_does_not_cancel_the_build_another_caller_waits_for(fresh_calendar, monkeypatch):
    """A follower's cancellation must not reach shared work (concepts/cancellation-safe-inflight-deduplication).

    One request abandoned by its client would otherwise leave every other waiting computation without
    the table it is waiting for.
    """
    module = market_calendar()
    seam = BuildSeam(BUILT, released=False)
    monkeypatch.setattr(module, "_build_in_subprocess", seam.build)

    first = asyncio.create_task(module.ensure_market_holidays())
    started: list[asyncio.Task] = [first]
    try:
        await _until(lambda: seam.calls, "the first caller did not start the build")
        second = asyncio.create_task(module.ensure_market_holidays())
        started.append(second)
        for _ in range(10):  # let the second caller reach its wait before it is cancelled
            await asyncio.sleep(0)
        second.cancel()
        await asyncio.gather(second, return_exceptions=True)
        seam.release.set()
        survivor = await asyncio.wait_for(first, timeout=5)
    finally:
        await _cancel(*started)

    assert survivor == BUILT_DAYS
    assert len(seam.calls) == 1


@pytest.mark.asyncio
async def test_a_failed_build_falls_back_to_weekends_and_is_tried_again_after_the_delay(fresh_calendar, monkeypatch, caplog):
    module = market_calendar()
    monkeypatch.setattr(module, "RETRY_AFTER_SECONDS", 0)
    seam = BuildSeam(RuntimeError("QuantLib could not start"), BUILT)
    monkeypatch.setattr(module, "_build_in_subprocess", seam.build)

    with capture_logs() as structured, caplog.at_level(logging.WARNING):
        fallback = await asyncio.wait_for(module.ensure_market_holidays(), timeout=5)

    # No holiday is known: weekends still apply wherever the table is read.
    assert fallback == frozenset()
    assert len(seam.calls) == 1
    logged = [entry for entry in structured if entry.get("log_level") in {"warning", "error", "critical"}]
    logged += [record for record in caplog.records if record.levelno >= logging.WARNING]
    assert logged, "a failed build must leave a trace in the log"

    # The delay has elapsed: a later caller tries again, and gets the table.
    assert await _call_until(module.ensure_market_holidays, BUILT_DAYS) == BUILT_DAYS
    assert len(seam.calls) == 2


@pytest.mark.asyncio
async def test_a_failed_build_is_not_tried_again_before_the_delay(fresh_calendar, monkeypatch):
    module = market_calendar()
    monkeypatch.setattr(module, "RETRY_AFTER_SECONDS", 3600)
    seam = BuildSeam(RuntimeError("QuantLib could not start"), BUILT)
    monkeypatch.setattr(module, "_build_in_subprocess", seam.build)

    assert await asyncio.wait_for(module.ensure_market_holidays(), timeout=5) == frozenset()
    # Every computation awaits the table: a broken build must not be launched again by each of them.
    for _ in range(3):
        assert await asyncio.wait_for(module.ensure_market_holidays(), timeout=5) == frozenset()
    assert len(seam.calls) == 1


@pytest.mark.asyncio
async def test_shutdown_returns_promptly_while_a_build_is_in_progress(fresh_calendar, monkeypatch):
    module = market_calendar()
    calls: list[tuple[int, int]] = []

    async def thirty_second_build(first_year: int, last_year: int) -> list[str]:
        calls.append((first_year, last_year))
        await asyncio.sleep(30)
        return list(BUILT)

    monkeypatch.setattr(module, "_build_in_subprocess", thirty_second_build)

    waiter = asyncio.create_task(module.ensure_market_holidays())
    try:
        await _until(lambda: calls, "the build never started")
        began = time.monotonic()
        await asyncio.wait_for(module.shutdown_market_holidays(), timeout=10)
        elapsed = time.monotonic() - began
    finally:
        await _cancel(waiter)

    assert elapsed < 1.0, f"shutdown waited {elapsed:.2f}s for a build it should have left behind"


@pytest.mark.asyncio
async def test_the_prewarm_runs_in_the_background_and_starts_one_build_however_often_it_is_called(fresh_calendar, monkeypatch):
    module = market_calendar()
    seam = BuildSeam(BUILT, released=False)
    monkeypatch.setattr(module, "_build_in_subprocess", seam.build)

    first = module.start_market_holiday_prewarm()
    second = module.start_market_holiday_prewarm()
    try:
        assert isinstance(first, asyncio.Task)
        assert isinstance(second, asyncio.Task)
        # Scheduled, not awaited: the caller got control back while the build cannot have finished.
        assert not first.done()
        await _until(lambda: seam.calls, "the prewarm never started the build")
        seam.release.set()
        await asyncio.wait_for(asyncio.gather(first, second), timeout=5)
    finally:
        await _cancel(first, second)

    assert len(seam.calls) == 1
    # What the prewarm built is what the first computation gets, without building again.
    assert await asyncio.wait_for(module.ensure_market_holidays(), timeout=5) == BUILT_DAYS
    assert len(seam.calls) == 1


# ---------------------------------------------------------------------------
# The real build process
# ---------------------------------------------------------------------------

SLOW_CHILD_ENV = "LIBREFOLIO_TEST_SLOW_CHILD_SECONDS"
# A `sitecustomize` placed first on PYTHONPATH runs at the start of every child interpreter. This
# one holds the child for as long as the variable says, before it imports anything: a build that is
# still running when shutdown arrives, without replacing any of the code under test.
SLOW_CHILD_SITECUSTOMIZE = textwrap.dedent(f'''
    """Test-only: hold a child interpreter at start-up while {SLOW_CHILD_ENV} is set."""
    import os
    import time

    _delay = os.environ.get("{SLOW_CHILD_ENV}")
    if _delay:
        time.sleep(float(_delay))
    ''')


def _children() -> dict[int, psutil.Process]:
    return {child.pid: child for child in psutil.Process().children(recursive=True)}


def _is_alive(process: psutil.Process) -> bool:
    try:
        return process.is_running() and process.status() != psutil.STATUS_ZOMBIE
    except psutil.Error:
        return False


def _is_resource_tracker(process: psutil.Process) -> bool:
    """multiprocessing's own helper: started once per interpreter, and meant to outlive a build."""
    try:
        return any("resource_tracker" in part for part in process.cmdline())
    except psutil.Error:
        return False


def _new_children(before: set[int]) -> list[psutil.Process]:
    """Live child processes started since `before` was taken, multiprocessing's helper aside."""
    return [process for pid, process in _children().items() if pid not in before and _is_alive(process) and not _is_resource_tracker(process)]


def _describe(processes: list[psutil.Process]) -> str:
    described = []
    for process in processes:
        try:
            described.append(f"{process.pid}: {' '.join(process.cmdline())[:200]}")
        except psutil.Error:
            described.append(str(process.pid))
    return "; ".join(described) or "none"


@pytest.mark.asyncio
async def test_shutdown_stops_a_real_build_process_that_is_still_running(fresh_calendar, monkeypatch, tmp_path):
    module = market_calendar()
    # multiprocessing's helper outlives any build by design: start it before the hold is armed, or it
    # would be held too, and outlive this process by the length of the hold.
    resource_tracker.ensure_running()
    held = tmp_path / "held_child"
    held.mkdir()
    (held / "sitecustomize.py").write_text(SLOW_CHILD_SITECUSTOMIZE)
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join(part for part in (str(held), os.environ.get("PYTHONPATH")) if part))
    monkeypatch.setenv(SLOW_CHILD_ENV, "30")
    before = set(_children())

    prewarm = module.start_market_holiday_prewarm()
    try:
        await _until(lambda: _new_children(before), "the build never started a child process", timeout=30)
        began = time.monotonic()
        await asyncio.wait_for(module.shutdown_market_holidays(), timeout=10)
        elapsed = time.monotonic() - began
        assert elapsed < 1.0, f"shutdown took {elapsed:.2f}s with a build still running"
        # Held for 30 s at start-up, the child can only be gone this soon if shutdown ended it — and it
        # is gone when shutdown returns, checked with nothing awaited in between. A cancelled build ends
        # its own process a moment later anyway, so a shutdown that only cancelled the build would pass
        # a check that waits.
        survivors = _new_children(before)
        assert not survivors, f"a build process outlived shutdown: {_describe(survivors)}"
        # Nor is anything left waiting for the process that is gone.
        await asyncio.wait_for(asyncio.gather(prewarm, return_exceptions=True), timeout=5)
    finally:
        leftovers = _new_children(before)
        for process in leftovers:
            process.kill()
        psutil.wait_procs(leftovers, timeout=5)
        await _cancel(prewarm)


BOUNDARY_PROBE = textwrap.dedent("""
    import asyncio
    import json
    import sys

    import backend.app.services.market_calendar as market_calendar

    imported_with_the_module = "QuantLib" in sys.modules


    async def build():
        try:
            return await market_calendar._build_in_subprocess(2025, 2025)
        finally:
            await market_calendar.shutdown_market_holidays()


    holidays = asyncio.run(build())
    print("BOUNDARY " + json.dumps({"imported_with_the_module": imported_with_the_module, "imported_after_the_build": "QuantLib" in sys.modules, "holidays": holidays}))
    """)


def test_a_real_build_runs_quantlib_in_its_own_process_never_in_the_web_process():
    """The decision the whole design rests on, checked where no test has imported QuantLib already.

    A fresh interpreter imports the module, as the web process does, and runs the real build: it must
    return the table without QuantLib ever entering that interpreter, and then exit — nothing of the
    build may keep it alive.
    """
    completed = subprocess.run([sys.executable, "-c", BOUNDARY_PROBE], cwd=REPO_ROOT, capture_output=True, text=True, timeout=120)

    assert completed.returncode == 0, completed.stderr[-4000:]
    lines = [line for line in completed.stdout.splitlines() if line.startswith("BOUNDARY ")]
    assert lines, completed.stdout[-2000:]
    probe = json.loads(lines[-1].removeprefix("BOUNDARY "))
    assert probe["imported_with_the_module"] is False, "importing market_calendar must not import QuantLib"
    assert probe["imported_after_the_build"] is False, "the build must run QuantLib in a child process"
    holidays = probe["holidays"]
    assert holidays == sorted(set(holidays))
    assert {"2025-01-09", "2025-04-18", "2025-08-15", "2025-12-25"} <= set(holidays)
    assert "2025-03-12" not in holidays


# ---------------------------------------------------------------------------
# The app lifespan
# ---------------------------------------------------------------------------


def _stub_the_rest_of_the_lifespan(monkeypatch, main) -> None:
    """Everything else the lifespan starts or stops, reduced to nothing, as the other lifespan tests do."""

    async def nothing(*_args, **_kwargs):
        return None

    async def catalog():
        return SimpleNamespace(status=SimpleNamespace(built_in_count=0, host_count=0, warning_count=0))

    shutdown_event = asyncio.Event()

    async def scheduler(event):
        await event.wait()

    monkeypatch.setattr(main, "validate_signal_runtime", lambda: SimpleNamespace(pandas_ta_classic_version="test", talib_version="test"))
    monkeypatch.setattr(main.SignalPluginRegistry, "auto_discover", lambda: None)
    monkeypatch.setattr(main.SignalPluginRegistry, "list_plugin_codes", lambda: [])
    monkeypatch.setattr(main.ToolPluginRegistry, "get_snapshot", lambda: SimpleNamespace(definitions=[], failures=[]))
    monkeypatch.setattr(main, "ensure_data_dirs", lambda: None)
    monkeypatch.setattr(main, "initialize_risk_scenario_catalog", catalog)
    monkeypatch.setattr(main, "seed_default_avatars", lambda: 0)
    monkeypatch.setattr(main, "ensure_database_exists", lambda: None)
    monkeypatch.setattr(main, "_initialize_global_settings", nothing)
    monkeypatch.setattr(main, "_prewarm_provider_caches", nothing)
    monkeypatch.setattr(main, "get_shutdown_event", lambda: shutdown_event)
    monkeypatch.setattr(main, "scheduler_loop", scheduler)
    monkeypatch.setattr(main, "shutdown_tool_executor", nothing)
    for registry in (main.AssetProviderRegistry, main.FXProviderRegistry, main.BRIMProviderRegistry):
        monkeypatch.setattr(registry, "shutdown_all_providers", lambda: None)
    monkeypatch.setattr(main, "shutdown_brim_parse_pool", lambda wait=False: None)
    monkeypatch.setattr(main, "close_all_caches", lambda: None)


@pytest.mark.asyncio
async def test_the_lifespan_prewarms_the_table_off_the_request_path_and_stops_it_at_shutdown(fresh_calendar, monkeypatch):
    module = market_calendar()
    main = importlib.import_module("backend.app.main")
    events: list[str] = []
    release = asyncio.Event()
    prewarms: list[asyncio.Task] = []

    def fake_prewarm() -> asyncio.Task:
        events.append("prewarm")
        task = asyncio.create_task(release.wait())
        prewarms.append(task)
        return task

    async def fake_shutdown_market_holidays() -> None:
        events.append("shutdown_market_holidays")
        release.set()

    async def fake_shutdown_quant_worker_pools() -> None:
        events.append("shutdown_quant_worker_pools")

    # Whichever way main reaches them: a name imported into main, or the module's attribute.
    for owner in (main, module):
        monkeypatch.setattr(owner, "start_market_holiday_prewarm", fake_prewarm, raising=False)
        monkeypatch.setattr(owner, "shutdown_market_holidays", fake_shutdown_market_holidays, raising=False)
    monkeypatch.setattr(main, "shutdown_quant_worker_pools", fake_shutdown_quant_worker_pools)
    _stub_the_rest_of_the_lifespan(monkeypatch, main)

    async def serve() -> None:
        async with main.lifespan(main.app):
            events.append("serving")
            assert len(prewarms) == 1, "startup must start the prewarm"
            # The build is still running: startup did not wait for it.
            assert not prewarms[0].done()

    try:
        # A startup that awaited the build would never reach `serving`.
        await asyncio.wait_for(serve(), timeout=15)
    finally:
        release.set()
        await asyncio.gather(*prewarms, return_exceptions=True)

    serving = events.index("serving")
    assert events[:serving] == ["prewarm"]
    assert sorted(events[serving + 1 :]) == ["shutdown_market_holidays", "shutdown_quant_worker_pools"]
