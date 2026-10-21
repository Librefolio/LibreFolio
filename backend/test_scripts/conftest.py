import contextlib
import os
import sqlite3
import sys
import warnings

import pytest

from backend.app.config import get_data_dir, is_test_mode
from backend.test_scripts import test_aiosqlite_guard as aiosqlite_guard

# The limit on failed sign-ins (F15) counts per process: the in-process apps of many files share one pytest process
# and its limiters, and the suites sign in wrongly on purpose. So it is off in every test process, as dev.py makes it
# for the lane's server: set once here, at import, for the code that runs before any fixture. Once is not enough:
# configure_test_runtime(), reached at import by setup_test_database() and its siblings, drops every LIBREFOLIO_* name
# the lane does not keep, this one included, at collection (lot E-15). Hence restore_login_limit, which puts the
# session's value back before each test that finds it missing. An explicit value still wins: setdefault keeps it.
# The limit's own tests turn it on, or remove it, after that fixture: their autouse fixtures and monkeypatch run later.
_LOGIN_LIMIT_VARIABLE = "LIBREFOLIO_LOGIN_LIMIT"
_SESSION_LOGIN_LIMIT = os.environ.setdefault(_LOGIN_LIMIT_VARIABLE, "off")

# Matches PRAGMA busy_timeout=30000 in backend/app/db/session.py: this fixture
# competes for the same write lock as the app, so it waits as long as the app.
_SEED_LOCK_TIMEOUT_S = 30.0

# Captured by pytest_sessionfinish, consumed by pytest_unconfigure.
# None means pytest_sessionfinish never ran (e.g. early collection error),
# in which case we let the interpreter shut down normally.
_exit_status = None


@pytest.fixture(scope="session", autouse=True)
def restore_registration_setting():
    """Make sure the global settings exist, and that registration is open.

    Almost every API test creates its own user through POST /auth/register, so
    the whole suite depends on `registration_mode` being `open`. The auth tests
    legitimately set it to `disabled` and restore it in a `finally`, but that
    restore is skipped when a run is killed mid-test (Ctrl-C, a crashed test
    server, a parallel Playwright run recreating the DB). The stale `disabled`
    then survives into the *next* run and makes ~50 unrelated tests fail with
    REGISTRATION_DISABLED — an error that points nowhere near the real cause.
    Any value other than `open` (`invite` included) closes registration to those
    tests just the same, so any other value is put back to `open`.

    Only the row is restored here: `LIBREFOLIO_REGISTRATION`, when set, wins over
    it and locks it, and no fixture can unset the environment of the lane's server.

    Seeding the rows, and not merely updating them, matters just as much. The
    settings are created by the app's startup hook, and every API module used to
    start its own server — so a module that wiped `global_settings` was silently
    repaired by the next module's startup. With one server for the whole run
    nobody repairs anything, and an `UPDATE` on a missing row does nothing at
    all: the tests then fail far from the wipe that caused it, with a 404 or an
    assertion about a setting "not initialized".

    The insert mirrors the app's own `initialize_global_settings()`, which is
    likewise "create only what is missing", so a suite that deliberately changes
    a value during the session is unaffected. One row differs: a missing
    `registration_mode` is inserted `open`, the lane's value, not the default — a
    new install starts by invitation (decision 36), and that default would close
    registration to every test that registers its own user.

    Being `autouse` this runs in **every** pytest process, so under `--workers N`
    all N workers reach this row within a second of each other — including the
    ones classified `pure`, whose "no DB" guarantee this fixture is the sole
    exception to. Hence the read-first fast path below, the explicit timeout (the
    stdlib default is 5s, a sixth of what the app's own engine allows) and the
    closing() wrapper: `with conn` commits but does not close, which would leak
    one connection per worker for the whole session and hold WAL checkpointing
    back.
    """
    if not is_test_mode():
        return

    db_path = get_data_dir() / "sqlite" / "app.db"
    if not db_path.exists():
        return

    try:
        from backend.app.schemas.settings import GLOBAL_SETTINGS_DEFAULTS  # noqa: PLC0415 — deliberate: fall back to {} when schemas are unavailable in this context
    except Exception:
        GLOBAL_SETTINGS_DEFAULTS = {}

    try:
        with contextlib.closing(sqlite3.connect(db_path, timeout=_SEED_LOCK_TIMEOUT_S)) as conn:
            # Read before writing. In the overwhelmingly common case every default
            # is already seeded and registration is already open, so the eight
            # workers that start within a second of each other take no write lock
            # at all — a WAL reader blocks nobody. The write path is then reserved
            # for the case it was written for: a previous run killed mid-test.
            present = {row[0] for row in conn.execute("SELECT key FROM global_settings")}
            missing = {k: v for k, v in GLOBAL_SETTINGS_DEFAULTS.items() if k not in present}
            registration_closed = conn.execute("SELECT 1 FROM global_settings WHERE key = 'registration_mode' AND value != 'open'").fetchone() is not None
            if not missing and not registration_closed:
                return

            with conn:
                for key, config in missing.items():
                    value = "open" if key == "registration_mode" else config["value"]
                    conn.execute(
                        "INSERT OR IGNORE INTO global_settings (key, value, value_type, description, updated_at) " "VALUES (?, ?, ?, ?, datetime('now'))",
                        (key, value, config["type"], config.get("description")),
                    )
                if registration_closed:
                    conn.execute("UPDATE global_settings SET value = 'open' WHERE key = 'registration_mode'")
    except sqlite3.OperationalError as exc:
        # "no such table" is the documented benign case: the DB is not migrated
        # yet and the suite's own setup will build it. Anything else — a lock
        # timeout above all — means registration may have stayed closed, and
        # the docstring explains what that costs: dozens of unrelated tests
        # failing with a message that points nowhere near here. Silence is what
        # makes that expensive, so this one says its name.
        if "no such table" not in str(exc):
            warnings.warn(
                f"could not restore registration_mode ({exc}); expect unrelated " "REGISTRATION_DISABLED / INVITE_REQUIRED failures across this run",
                stacklevel=2,
            )
    except sqlite3.Error:
        pass


@pytest.fixture(autouse=True)
def restore_login_limit():
    """Put the session's ``LIBREFOLIO_LOGIN_LIMIT`` back for a test that starts without it, and remove it at teardown.

    The lane's configuration drops it at collection (lot E-15); a value present when the test starts is left alone, and
    the limit's own tests, whose fixtures and monkeypatch run after this one, still turn it on or remove it.
    """
    # A MonkeyPatch of its own, not the monkeypatch fixture: requested here, that one would be set up before the
    # fixtures of every module and test, and so undo each test's own patches after their teardowns instead of before.
    with pytest.MonkeyPatch.context() as patch:
        if _LOGIN_LIMIT_VARIABLE not in os.environ:
            patch.setenv(_LOGIN_LIMIT_VARIABLE, _SESSION_LOGIN_LIMIT)
        yield


#: The limit on refused hosting panel credentials in every test process: none in practice (lot H-61).
_TEST_PANEL_ATTEMPT_LIMIT = 1_000_000


@pytest.fixture(autouse=True)
def lift_panel_attempt_limit():
    """Give each test a limiter of the hosting panel's refused credentials of its own, with no limit in practice (H-61).

    The limit counts per process and per address, like the one on sign-ins, which is off in every test process (above),
    and the in-process apps of many files refuse panel credentials on purpose, from httpx's one client address: with the
    real limit a file's own 401 tests would meet a 429 (PANEL-012 alone sends 36 refusals). The limit's own tests
    (``test_hosting_panel_access.py``) replace this limiter, after this fixture, through their monkeypatch.
    """
    from backend.app.services.platform.hosting_panel import access  # noqa: PLC0415 — the app's modules load after the lane's configuration
    from backend.app.utils.runtime.rate_window import SlidingWindowLimiter  # noqa: PLC0415

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(access, "PANEL_ATTEMPTS", SlidingWindowLimiter(_TEST_PANEL_ATTEMPT_LIMIT, access.PANEL_ATTEMPT_WINDOW_SECONDS))
        yield


# The aiosqlite leak guard (J-6) is installed here, when this conftest is imported: before any test module of the
# run, and therefore any aiosqlite connection, exists. Idempotent.
aiosqlite_guard.install()


@pytest.fixture(autouse=True)
def _aiosqlite_leak_guard(request):
    """Fail, at its own teardown, a test that leaves open an aiosqlite connection it created.

    An open aiosqlite connection that outlives its test is closed later by the garbage collector, and that close
    can bind to a closed event loop and kill the connection's worker thread: "Event loop is closed", reported as a
    PytestUnhandledThreadExceptionWarning on whichever unrelated test happens to be running (C-93 had to track
    seven such leaks down by hand). Checked here, the same leak is an ERROR at the teardown of the test that
    caused it, with the connection's creation stack — the attribution C-93 lacked.

    The window this fixture opens is the test. Being autouse and function-scoped, it is set up before every other
    function-scoped fixture and torn down after all of them, so:

    - a fixture that closes its session and disposes its engine in its teardown (``real_db_session``,
      ``db_session``) has done so before the check runs, and its test is clean;
    - a connection opened by a module-, class- or session-scoped fixture during its setup was opened before the
      window, and is not attributed to the test that happened to trigger that setup;
    - pytest-asyncio's function loop is already closed when the check runs, which costs nothing: the check reads
      attributes and never touches a loop.

    The rule, what it deliberately leaves alone and the explicit exceptions list live in
    ``test_aiosqlite_guard.py``; its self-tests are the utils action ``gate-aiosqlite-leak``. The guard only
    reports: stopping a leaked connection from here could meet a closed current loop itself.
    """
    with aiosqlite_guard.leak_window(request.node.nodeid) as window:
        yield
    leaks = aiosqlite_guard.find_leaks(window)
    if leaks:
        pytest.fail(aiosqlite_guard.format_leak_report(window, leaks), pytrace=False)


def pytest_sessionfinish(session, exitstatus):
    global _exit_status
    _exit_status = int(exitstatus)


def _release_process_pools():
    """Join worker processes by hand, because os._exit() below skips atexit.

    A BRIM parse runs in a ``forkserver``-backed process pool. The pool is
    normally reaped by the ``atexit`` handler that ``concurrent.futures``
    registers — and ``os._exit`` never runs it. What survives is not a zombie
    but a live forkserver plus its workers, re-parented to init and still
    holding the stdout they inherited from pytest. A run piped into ``tee``
    therefore never sees EOF and hangs forever, which is why the project rule
    used to be "never pipe a test run".

    Measured on this exact shape: shutdown(wait=False) immediately before
    os._exit still hangs — the management thread has no chance to send the
    sentinels. Only the join closes the pipe.

    Looked up through sys.modules so a suite that never parsed a file does not
    import the module (and build a pool) just to tear it down.
    """
    pool_module = sys.modules.get("backend.app.services.brim.brim_parse_pool")
    if pool_module is not None:
        with contextlib.suppress(Exception):
            pool_module.shutdown_pool(wait=True)


def pytest_unconfigure(config):
    """Force process exit once pytest is fully done, including terminal reporting.

    The uvicorn test server runs in a background thread, but Python's
    threading._shutdown() waits for ThreadPoolExecutor worker threads
    (used internally by asyncio/uvicorn) which never terminate.
    os._exit() bypasses this. It must run in pytest_unconfigure (not
    pytest_sessionfinish) because pytest_sessionfinish is called *before*
    the terminal reporter prints the FAILURES section and summary line —
    exiting there silently swallows all failure diagnostics.

    And it must flush first, for the same reason. os._exit() skips the
    interpreter's own flush, so whatever is still sitting in the stdout buffer
    is discarded. On a terminal that costs nothing (line-buffered), but every
    run the test runner records goes through a **pipe**, where the buffer is a
    few KB and only full blocks have been written out. The tail is exactly what
    is lost — and the tail is the FAILURES section and the summary line, the two
    things this hook was moved here to preserve. Measured before the fix: every
    per-unit backend log in .testLog ended mid-line at "[100%]" with no summary,
    and `pytest --collect-only` redirected to a file produced zero bytes.
    """
    if _exit_status is not None:
        for stream in (sys.stdout, sys.stderr):
            with contextlib.suppress(Exception):
                stream.flush()
        _release_process_pools()
        os._exit(_exit_status)
