import contextlib
import os
import sqlite3
import sys
import warnings

import pytest

from backend.app.config import get_data_dir, is_test_mode

# Matches PRAGMA busy_timeout=30000 in backend/app/db/session.py: this fixture
# competes for the same write lock as the app, so it waits as long as the app.
_SEED_LOCK_TIMEOUT_S = 30.0

# Captured by pytest_sessionfinish, consumed by pytest_unconfigure.
# None means pytest_sessionfinish never ran (e.g. early collection error),
# in which case we let the interpreter shut down normally.
_exit_status = None


@pytest.fixture(scope="session", autouse=True)
def restore_registration_setting():
    """Make sure the global settings exist, and that registration is on.

    Almost every API test creates its own user through POST /auth/register, so
    the whole suite depends on `enable_registration` being true. The auth tests
    legitimately flip it to false and restore it in a `finally`, but that
    restore is skipped when a run is killed mid-test (Ctrl-C, a crashed test
    server, a parallel Playwright run recreating the DB). The stale `false`
    then survives into the *next* run and makes ~50 unrelated tests fail with
    "New user registration is disabled" — an error that points nowhere near the
    real cause.

    Seeding the rows, and not merely updating them, matters just as much. The
    settings are created by the app's startup hook, and every API module used to
    start its own server — so a module that wiped `global_settings` was silently
    repaired by the next module's startup. With one server for the whole run
    nobody repairs anything, and an `UPDATE` on a missing row does nothing at
    all: the tests then fail far from the wipe that caused it, with a 404 or an
    assertion about a setting "not initialized".

    The insert mirrors the app's own `initialize_global_settings()`, which is
    likewise "create only what is missing", so a suite that deliberately changes
    a value during the session is unaffected.

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
        from backend.app.schemas.settings import GLOBAL_SETTINGS_DEFAULTS
    except Exception:
        GLOBAL_SETTINGS_DEFAULTS = {}

    try:
        with contextlib.closing(sqlite3.connect(db_path, timeout=_SEED_LOCK_TIMEOUT_S)) as conn:
            # Read before writing. In the overwhelmingly common case every default
            # is already seeded and registration is already on, so the eight
            # workers that start within a second of each other take no write lock
            # at all — a WAL reader blocks nobody. The write path is then reserved
            # for the case it was written for: a previous run killed mid-test.
            present = {row[0] for row in conn.execute("SELECT key FROM global_settings")}
            missing = {k: v for k, v in GLOBAL_SETTINGS_DEFAULTS.items() if k not in present}
            registration_off = conn.execute("SELECT 1 FROM global_settings WHERE key = 'enable_registration' AND value != 'true'").fetchone() is not None
            if not missing and not registration_off:
                return

            with conn:
                for key, config in missing.items():
                    conn.execute(
                        "INSERT OR IGNORE INTO global_settings (key, value, value_type, description, updated_at) " "VALUES (?, ?, ?, ?, datetime('now'))",
                        (key, config["value"], config["type"], config.get("description")),
                    )
                if registration_off:
                    conn.execute("UPDATE global_settings SET value = 'true' WHERE key = 'enable_registration'")
    except sqlite3.OperationalError as exc:
        # "no such table" is the documented benign case: the DB is not migrated
        # yet and the suite's own setup will build it. Anything else — a lock
        # timeout above all — means registration may have stayed disabled, and
        # the docstring explains what that costs: dozens of unrelated tests
        # failing with a message that points nowhere near here. Silence is what
        # makes that expensive, so this one says its name.
        if "no such table" not in str(exc):
            warnings.warn(
                f"could not restore enable_registration ({exc}); expect unrelated " "'registration is disabled' failures across this run",
                stacklevel=2,
            )
    except sqlite3.Error:
        pass


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
    pool_module = sys.modules.get("backend.app.services.brim_parse_pool")
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
