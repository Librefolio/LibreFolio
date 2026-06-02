def pytest_sessionfinish(session, exitstatus):
    import os; os._exit(exitstatus)
