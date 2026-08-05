import os
import sqlite3

import pytest

from backend.app.config import get_data_dir, is_test_mode

# Captured by pytest_sessionfinish, consumed by pytest_unconfigure.
# None means pytest_sessionfinish never ran (e.g. early collection error),
# in which case we let the interpreter shut down normally.
_exit_status = None


@pytest.fixture(scope="session", autouse=True)
def restore_registration_setting():
    """Re-enable user registration in the test DB before the session starts.

    Almost every API test creates its own user through POST /auth/register, so
    the whole suite depends on `enable_registration` being true. The auth tests
    legitimately flip it to false and restore it in a `finally`, but that
    restore is skipped when a run is killed mid-test (Ctrl-C, a crashed test
    server, a parallel Playwright run recreating the DB). The stale `false`
    then survives into the *next* run and makes ~50 unrelated tests fail with
    "New user registration is disabled" — an error that points nowhere near the
    real cause.

    This is cheap insurance, not a substitute for the per-test cleanup: it runs
    once at session start, so tests that deliberately disable registration
    during the session are unaffected.
    """
    if not is_test_mode():
        return

    db_path = get_data_dir() / "sqlite" / "app.db"
    if not db_path.exists():
        return

    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE global_settings SET value = 'true' WHERE key = 'enable_registration'")
    except sqlite3.Error:
        # The DB may not be migrated yet on a first run; the suite's own
        # setup will build it. Never block collection over this guard.
        pass


def pytest_sessionfinish(session, exitstatus):
    global _exit_status
    _exit_status = int(exitstatus)


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
        os._exit(_exit_status)
