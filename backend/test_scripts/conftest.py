import os

# Captured by pytest_sessionfinish, consumed by pytest_unconfigure.
# None means pytest_sessionfinish never ran (e.g. early collection error),
# in which case we let the interpreter shut down normally.
_exit_status = None


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
