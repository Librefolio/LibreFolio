"""
Shared pytest configuration for backend API tests.

Forces process exit after test session to prevent hanging when the
uvicorn test server thread's ThreadPoolExecutor blocks Python shutdown.
"""

import os


def pytest_sessionfinish(session, exitstatus):
    """Force process exit after all tests complete.

    The uvicorn test server runs in a daemon thread, but Python's
    threading._shutdown() waits for ThreadPoolExecutor worker threads
    (used internally by asyncio/uvicorn) which never terminate.
    os._exit() bypasses this, exiting immediately after pytest is done.
    """
    os._exit(exitstatus)

