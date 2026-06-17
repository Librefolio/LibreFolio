import os


def pytest_sessionfinish(session, exitstatus):
    os._exit(exitstatus)
