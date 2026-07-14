---
title: "conftest.py os._exit() in pytest_sessionfinish swallowed every FAILURES/summary report"
category: problem
status: resolved
date: 2026-07-13
tags: [backend, testing, pytest, infra]
related:
  - problems/test-transaction-implied-constructor-mismatch
---

# Problem: `os._exit()` in `pytest_sessionfinish` Swallowed All Failure Diagnostics

## Summary

`backend/test_scripts/conftest.py` force-exits the process right after tests finish, to
avoid a real hang (see below). But it did so in the `pytest_sessionfinish` hook, which
pytest's own terminal reporter *also* implements as a hook. Whichever runs last wins, and
`os._exit()` ends the process before the reporter gets to print the `FAILURES` section and
the final `X failed, Y passed` line — for every run, pass or fail, whenever pytest's stdout
isn't a tty (e.g. piped through `tee`, as `./dev.py test` always does). This made every test
failure across the whole backend suite invisible: you'd see `FAILED test_name` but never the
traceback, assertion diff, or short summary.

## Root Cause

Pytest's session lifecycle (`_pytest/main.py::wrap_session`) calls
`config.hook.pytest_sessionfinish(...)` — which runs *all* registered `pytest_sessionfinish`
implementations, including the built-in `TerminalReporter`'s (which prints `FAILURES` +
summary) — and only *after that fully completes* does it call `config._ensure_unconfigure()`,
which fires `pytest_unconfigure`. The original conftest hook:

```python
def pytest_sessionfinish(session, exitstatus):
    os._exit(exitstatus)
```

calls `os._exit()` as one of the `pytest_sessionfinish` implementations — with no guaranteed
ordering against the terminal reporter's own implementation of the same hook. In practice the
process dies before the reporter's output ever gets flushed/printed.

## Solution

Split the two concerns across two hooks: capture the exit status in `pytest_sessionfinish`
(cheap, no exit), and do the actual `os._exit()` in `pytest_unconfigure` — which pytest
guarantees runs *after* `pytest_sessionfinish` (and hence after the reporter printed
everything):

```python
_exit_status = None

def pytest_sessionfinish(session, exitstatus):
    global _exit_status
    _exit_status = int(exitstatus)

def pytest_unconfigure(config):
    if _exit_status is not None:
        os._exit(_exit_status)
```

The `None` guard preserves the original fallback: if `pytest_sessionfinish` never ran (e.g. a
config/collection error before the session started), don't force-exit — there's no lingering
server thread to worry about yet, so let the interpreter shut down normally.

## Why the force-exit exists at all

Documented at introduction (commit `b4b77e70`, later trimmed): the uvicorn test server used by
API tests runs in a background thread; Python's normal interpreter shutdown
(`threading._shutdown()`) waits on internal `ThreadPoolExecutor` workers that never terminate,
hanging the whole process after tests are otherwise done. `os._exit()` bypasses that — this
behavior is still required and was preserved, just moved later in the lifecycle.

## Impact

This bug had been silently hiding every backend test failure's root cause for an unknown
period — anyone debugging a `FAILED` line only ever saw the bare test name, never *why*. Fixed
as a prerequisite for a full-suite triage pass (see
[[problems/test-transaction-implied-constructor-mismatch]] for one of the failures this
unblocked diagnosing).

## Source files

| Role | Path |
|------|------|
| Fix | `backend/test_scripts/conftest.py` |
