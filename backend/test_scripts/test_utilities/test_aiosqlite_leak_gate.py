"""
Gate: the aiosqlite leak guard sees a leak, and only a leak (J-6).

``backend/test_scripts/conftest.py`` runs ``backend/test_scripts/test_aiosqlite_guard.py`` around every backend test:
a test that leaves open an aiosqlite connection it created fails at its own teardown. Left alone, such a connection
is closed later by the garbage collector against a closed event loop, its worker thread dies with "Event loop is
closed", and pytest blames whichever unrelated test happens to be running (C-93).

A guard asserts an absence, and an absence is also what a blind guard reports. So every property is proven here as
a presence first, then as the absence it permits:

- the C-93 shape — an in-memory engine queried, its session closed, the engine not disposed — is reported, with a
  creation stack that reaches this file across SQLAlchemy's greenlet; once the engine is disposed it is not;
- a connection closed before the check is tracked but not reported: ``async with``, ``engine.dispose()``, and a
  ``NullPool`` session closed without any dispose (the shape of the app's own engine);
- a connection created in another thread is not tracked, while one created in the main thread under the same window
  is;
- a connection created before a window opened is not attributed to it, though the window open at the time has it;
- an exception entry matching the creating nodeid at a boundary excuses it, any other entry does not; an entry
  without a prefix or a reason is refused, and the shipped list is well-formed and names existing paths;
- a tracked object without aiosqlite's private ``_connection`` makes the check raise instead of pass;
- ``install()`` wraps once however often it runs, and the conftest's window is open around this very test;
- end to end, in a child pytest that loads the real conftest: the leaking test — and only it — errors at its own
  teardown with the rule and the fix, while a fixture that disposes its engine, a module-scoped engine connected
  before the window, and the test that runs after the leak stay clean.

Each test opens windows of its own inside the conftest's and closes everything it opened before it returns, so the
real guard stays green on this file.

Pure: private in-memory SQLite databases, a worker thread of its own, and a child pytest on a synthetic file under
tmp_path — no server, no network, no writes outside tmp_path. The lane database is read only by the conftest's own
session fixture, as in every pytest process.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import threading
import xml.etree.ElementTree as ElementTree
from pathlib import Path

import aiosqlite
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.test_scripts import test_aiosqlite_guard as guard
from backend.test_scripts.test_utils import print_section, print_success

# Compared with code objects' co_filename, which carries the path the module was imported from: not resolved.
THIS_FILE = os.path.abspath(__file__)
REPO_ROOT = Path(THIS_FILE).parents[3]

# The attribution of the synthetic windows: a nodeid in pytest's shape, owned by these tests alone.
SYNTHETIC_MODULE = "backend/test_scripts/test_services/test_synthetic_leaks.py"
SYNTHETIC_NODEID = f"{SYNTHETIC_MODULE}::TestShape::test_leaks[case]"


def _tracked(window: guard.LeakWindow) -> list:
    """Every connection ``window`` tracked, reported or not."""
    return [entry.connection for entry in window.tracked]


def _leaked(window: guard.LeakWindow, **kwargs) -> list:
    """The connections ``find_leaks`` reports for ``window``."""
    return [entry.connection for entry in guard.find_leaks(window, **kwargs)]


async def _driver_connection(connection: AsyncConnection) -> aiosqlite.Connection:
    """The aiosqlite connection behind a checked-out SQLAlchemy connection, through its public raw connection."""
    return (await connection.get_raw_connection()).driver_connection


# =============================================================================
# Presence: what the guard must see
# =============================================================================


@pytest.mark.asyncio
async def test_c93_shape_is_reported_until_its_engine_is_disposed():
    """An in-memory engine queried and its session closed, the engine not disposed: its pooled connection is a leak."""
    print_section("C-93 shape: session closed, engine not disposed")
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        with guard.leak_window(SYNTHETIC_NODEID) as window:
            session = AsyncSession(engine)
            await session.execute(text("SELECT 1"))
            await session.close()
            async with engine.connect() as connection:  # StaticPool: the very connection the session used
                pooled = await _driver_connection(connection)

            leaks = guard.find_leaks(window)
            assert [entry.connection for entry in leaks] == [pooled]
            assert leaks[0].nodeid == SYNTHETIC_NODEID
            # Created inside SQLAlchemy's greenlet, whose own stack never reaches a test: the stack must still name this one.
            this_test = test_c93_shape_is_reported_until_its_engine_is_disposed.__name__
            assert any(frame.filename == THIS_FILE and frame.function == this_test for frame in leaks[0].stack), leaks[0].stack

            report = guard.format_leak_report(window, leaks)
            print(report)
            assert f"{SYNTHETIC_NODEID} left 1 aiosqlite connection(s) open at its teardown" in report
            assert "Rule: no test may leave behind an open aiosqlite connection it created." in report
            assert f"{os.path.relpath(THIS_FILE, REPO_ROOT)}:" in report
            assert "finally: await engine.dispose()" in report

            await engine.dispose()
            # Still tracked and still alive: the absence below is the dispose, not a blind guard.
            assert _tracked(window) == [pooled]
            assert guard.find_leaks(window) == []
    finally:
        await engine.dispose()
    print_success("reported with a stack reaching the test while open, silent once the engine is disposed")


@pytest.mark.asyncio
async def test_a_tracked_object_without_the_private_attribute_fails_loudly():
    """The guard reads aiosqlite 0.22.1's private ``_connection``; without it the check must raise, never pass."""
    print_section("aiosqlite without _connection: the check raises")
    with guard.leak_window(SYNTHETIC_NODEID) as window:
        unopened = aiosqlite.connect(":memory:")  # constructed, never awaited: no thread started, no sqlite3 connection
        assert _tracked(window) == [unopened]
        assert guard.find_leaks(window) == []  # control: the attribute present and None, so closed

        del unopened._connection
        try:
            with pytest.raises(guard.AiosqliteGuardOutdated, match="The guard must be updated"):
                guard.find_leaks(window)
        finally:
            unopened._connection = None  # its __del__ reads the attribute too
    print_success("a missing _connection raises AiosqliteGuardOutdated")


# =============================================================================
# Absence: what the guard must leave alone
# =============================================================================


@pytest.mark.asyncio
async def test_a_connection_closed_before_the_check_is_tracked_but_not_reported():
    """``async with``, ``engine.dispose()`` and a NullPool session close all close before the check: not leaks."""
    print_section("Closed before the check: tracked, not reported")
    with guard.leak_window(SYNTHETIC_NODEID) as window:
        async with aiosqlite.connect(":memory:") as direct:
            await direct.execute("SELECT 1")

        disposed_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        try:
            async with AsyncSession(disposed_engine) as session:
                pooled = await _driver_connection(await session.connection())
        finally:
            await disposed_engine.dispose()

        # NullPool, like the app's own engine: closing the session closes its connection, no dispose involved.
        unpooled_engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=NullPool)
        try:
            async with AsyncSession(unpooled_engine) as session:
                unpooled = await _driver_connection(await session.connection())
            assert _tracked(window) == [direct, pooled, unpooled]
            assert guard.find_leaks(window) == []
        finally:
            await unpooled_engine.dispose()
    print_success("three connections tracked, none reported")


@pytest.mark.asyncio
async def test_a_connection_created_in_another_thread_is_not_tracked():
    """A connection born in another thread lives on that thread's loop (the in-process uvicorn's): not the test's."""
    print_section("Another thread: not tracked")
    opened = threading.Event()
    checked = threading.Event()
    box: dict = {}

    async def hold_open() -> None:
        async with aiosqlite.connect(":memory:") as connection:
            await connection.execute("SELECT 1")
            box["connection"] = connection
            opened.set()
            await asyncio.to_thread(checked.wait, 60)

    def run_own_loop() -> None:
        try:
            asyncio.run(hold_open())
        except BaseException as exc:  # handed to the main thread, which fails with it
            box["error"] = exc
            opened.set()

    worker = threading.Thread(target=run_own_loop, name="aiosqlite-leak-gate-worker")
    with guard.leak_window(SYNTHETIC_NODEID) as window:
        worker.start()
        try:
            assert await asyncio.to_thread(opened.wait, 60), "the worker thread never opened its connection"
            assert "error" not in box, box.get("error")
            assert box["connection"]._connection is not None  # open right now, by the very attribute the guard reads
            async with aiosqlite.connect(":memory:") as own:  # control: born in the main thread, under the same window
                await own.execute("SELECT 1")
                assert _tracked(window) == [own]
                assert _leaked(window) == [own]
        finally:
            checked.set()
            await asyncio.to_thread(worker.join, 60)
    assert not worker.is_alive()
    assert "error" not in box, box.get("error")
    print_success("the other thread's open connection is untracked; the main thread's is tracked and reported")


@pytest.mark.asyncio
async def test_a_connection_created_before_a_window_is_not_attributed_to_it(request):
    """A window owns what is born inside it: an older connection, still open, belongs to the window open at its birth."""
    print_section("Created before the window: not attributed to it")
    async with aiosqlite.connect(":memory:") as earlier:
        await earlier.execute("SELECT 1")
        conftest_window = next(window for window in guard.active_leak_windows() if window.nodeid == request.node.nodeid)
        assert any(entry.connection is earlier for entry in conftest_window.tracked)  # trackable, and tracked there
        with guard.leak_window(SYNTHETIC_NODEID) as window:
            async with aiosqlite.connect(":memory:") as later:
                await later.execute("SELECT 1")
                # Both are open right now; only the one born inside this window is its leak.
                assert _leaked(window) == [later]
    print_success("only the connection born inside the window is attributed to it")


@pytest.mark.asyncio
async def test_an_exception_entry_excuses_its_own_nodeid_at_a_boundary_only():
    """An entry excuses the nodeid it names or a parent of it — directory, module, class, test — never a namesake."""
    print_section("Exceptions: matching nodeid prefixes only")
    excusing = (
        SYNTHETIC_NODEID,
        f"{SYNTHETIC_MODULE}::TestShape::test_leaks",
        f"{SYNTHETIC_MODULE}::TestShape",
        SYNTHETIC_MODULE,
        "backend/test_scripts/test_services",
        "backend/test_scripts/test_services/",
    )
    not_excusing = (
        f"{SYNTHETIC_MODULE}::TestShape::test_leaks[other]",
        f"{SYNTHETIC_MODULE}::TestShape::test_lea",
        f"{SYNTHETIC_MODULE}::TestSha",
        "backend/test_scripts/test_services/test_synthetic",
        "backend/test_scripts/test_serv",
        "backend/test_scripts/test_services/test_other.py",
    )
    with guard.leak_window(SYNTHETIC_NODEID) as window:
        async with aiosqlite.connect(":memory:") as connection:
            await connection.execute("SELECT 1")
            assert _leaked(window, exceptions=()) == [connection]
            for prefix in excusing:
                assert guard.find_leaks(window, exceptions=((prefix, "synthetic: owned by a module fixture"),)) == [], prefix
            for prefix in not_excusing:
                assert _leaked(window, exceptions=((prefix, "synthetic: owned by a module fixture"),)) == [connection], prefix
    print_success(f"{len(excusing)} matching prefixes excuse, {len(not_excusing)} namesakes do not")


def test_an_exception_entry_needs_a_prefix_and_a_reason_and_the_shipped_list_is_sound():
    """A blank prefix would excuse everything and a blank reason explains nothing: both refuse the whole list."""
    print_section("Exceptions: refused without a prefix or a reason")
    malformed = (
        ("", "owned by a module fixture"),
        ("   ", "owned by a module fixture"),
        (SYNTHETIC_MODULE, ""),
        (SYNTHETIC_MODULE, "   "),
        (SYNTHETIC_MODULE, None),
        (SYNTHETIC_MODULE,),
        SYNTHETIC_MODULE,
    )
    with guard.leak_window(SYNTHETIC_NODEID) as window:
        for entry in malformed:
            with pytest.raises(ValueError, match=r"must be \(nodeid prefix, one-line reason\)"):
                guard.find_leaks(window, exceptions=(entry,))
        assert guard.find_leaks(window) == []  # the shipped list passes the same validation
    for prefix, reason in guard.AIOSQLITE_LEAK_EXCEPTIONS:
        named = REPO_ROOT / prefix.split("::", 1)[0]
        assert named.exists(), f"stale exception {prefix!r} ({reason}): {named} does not exist"
    print_success(f"{len(malformed)} malformed entries refused; {len(guard.AIOSQLITE_LEAK_EXCEPTIONS)} shipped exception(s), all sound")


# =============================================================================
# Wiring: the conftest arms the guard around every test
# =============================================================================


def test_install_wraps_once_and_the_conftest_window_is_open_around_this_test(request):
    """The conftest installed the wrapper at import and opened a window for this test, under its own nodeid."""
    print_section("Wiring: one wrapper, the conftest's window around this test")
    assert [window.nodeid for window in guard.active_leak_windows()] == [request.node.nodeid]

    installed = aiosqlite.core.Connection.__init__
    guard.install()
    guard.install()
    assert aiosqlite.core.Connection.__init__ is installed
    assert not hasattr(installed.__wrapped__, "__wrapped__")  # one wrapper, directly over aiosqlite's own __init__

    with guard.leak_window(SYNTHETIC_NODEID) as window:
        unopened = aiosqlite.connect(":memory:")  # constructed, never awaited: no thread started, no sqlite3 connection
    assert _tracked(window) == [unopened]  # registered once, however many install() calls
    assert [window.nodeid for window in guard.active_leak_windows()] == [request.node.nodeid]
    print_success("one wrapper; this test's window open, the inner one closed")


SYNTHETIC_SUITE = '''
"""Synthetic tests: test_aiosqlite_leak_gate.py runs them in a child pytest that loads the real conftest."""

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

# Keeps the leaked engine reachable past its test: the guard must see it open, and no collection may race the check.
KEPT = []


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def module_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.connect() as connection:  # module setup: before the window of the test that triggers it
        await connection.execute(text("SELECT 1"))
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def disposed_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_leaks_an_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    KEPT.append(engine)
    async with AsyncSession(engine) as session:
        await session.execute(text("SELECT 1"))


@pytest.mark.asyncio
async def test_uses_a_fixture_that_disposes(disposed_engine):
    async with AsyncSession(disposed_engine) as session:
        await session.execute(text("SELECT 1"))


@pytest.mark.asyncio(loop_scope="module")
async def test_reuses_a_module_engine_connected_before_its_window(module_engine):
    async with AsyncSession(module_engine) as session:  # StaticPool: the connection module setup opened
        await session.execute(text("SELECT 1"))


def test_runs_after_the_leak():
    pass
'''


def test_the_conftest_fails_the_leaking_test_at_its_own_teardown(tmp_path):
    """A child pytest with the real conftest as a plugin: the leak is an ERROR at the leaking test's teardown, only there."""
    print_section("End to end: a child pytest under the real conftest")
    (tmp_path / "pytest.ini").write_text("[pytest]\nasyncio_default_fixture_loop_scope = function\n", encoding="utf-8")
    (tmp_path / "test_synthetic_leaks.py").write_text(SYNTHETIC_SUITE, encoding="utf-8")
    junit = tmp_path / "junit.xml"
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(filter(None, (str(REPO_ROOT), os.environ.get("PYTHONPATH"))))}
    command = [
        sys.executable,
        "-m",
        "pytest",
        "test_synthetic_leaks.py",
        "-c",
        "pytest.ini",
        "--rootdir",
        str(tmp_path),
        "-p",
        "backend.test_scripts.conftest",
        "-p",
        "no:cacheprovider",
        f"--junitxml={junit}",
    ]
    result = subprocess.run(command, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300, check=False)
    output = f"exit {result.returncode}\n{result.stdout}\n{result.stderr}"
    assert junit.exists(), output

    problems = {case.get("name"): [child for child in case if child.tag in ("failure", "error", "skipped")] for case in ElementTree.parse(junit).getroot().iter("testcase")}
    assert set(problems) == {
        "test_leaks_an_engine",
        "test_uses_a_fixture_that_disposes",
        "test_reuses_a_module_engine_connected_before_its_window",
        "test_runs_after_the_leak",
    }, output
    leak = problems.pop("test_leaks_an_engine")
    assert [child.tag for child in leak] == ["error"], output
    message = f"{leak[0].get('message')}\n{leak[0].text}"
    print(leak[0].text)
    assert "failed on teardown" in message, output
    assert "test_synthetic_leaks.py::test_leaks_an_engine left 1 aiosqlite connection(s) open at its teardown" in message, output
    assert "Rule: no test may leave behind an open aiosqlite connection it created." in message, output
    assert "finally: await engine.dispose()" in message, output
    assert problems == {name: [] for name in problems}, output
    assert result.returncode == 1, output
    print_success("the leaking test errors at its own teardown; the disposing fixture, the module engine and the next test pass")
