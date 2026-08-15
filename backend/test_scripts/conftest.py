import contextlib
import os
import sqlite3
import sys

import pytest

from backend.app.config import get_data_dir, is_test_mode

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
        with sqlite3.connect(db_path) as conn:
            for key, config in GLOBAL_SETTINGS_DEFAULTS.items():
                conn.execute(
                    "INSERT OR IGNORE INTO global_settings (key, value, value_type, description, updated_at) "
                    "VALUES (?, ?, ?, ?, datetime('now'))",
                    (key, config["value"], config["type"], config.get("description")),
                )
            conn.execute("UPDATE global_settings SET value = 'true' WHERE key = 'enable_registration'")
    except sqlite3.Error:
        # The DB may not be migrated yet on a first run; the suite's own
        # setup will build it. Never block collection over this guard.
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
    """
    if _exit_status is not None:
        _release_process_pools()
        os._exit(_exit_status)
