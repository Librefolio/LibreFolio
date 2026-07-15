---
title: "--coverage never reached frontend E2E Playwright runs (stale _COVERAGE_MODE import)"
category: problem
status: resolved
date: 2026-07-14
tags: [testing, test-runner, coverage, python, infra]
related: [[problems/resume-mode-stale-import]]
---

# Problem: `--coverage` Flag Never Propagated to Frontend E2E Runs

## Summary

`./dev.py test --coverage --fresh-run all` reported success and produced a backend
`htmlcov/` report, but silently never instrumented the frontend E2E (Playwright) run: no
`.coverage_data/frontend` directory and no `htmlcov-frontend/` were ever produced, so the
combined coverage numbers the user was analyzing under-counted every code path only exercised
by E2E specs. Root cause is the exact same class of bug as
[[problems/resume-mode-stale-import]], but in a different module: `scripts/test_runner/
_suites.py` did `from ._common import _COVERAGE_MODE` at import time, so its 3 internal call
sites (`run_all_tests`, `run_all_backend_tests`, `run_all_frontend_tests`) always read the
frozen default (`False`) even after `_cli.py` set `_common._COVERAGE_MODE = True` in response
to the `--coverage` flag.

## Root Cause

```python
# _common.py
_COVERAGE_MODE = False  # default

# _cli.py (after argparse)
_common._COVERAGE_MODE = args.coverage  # mutates the module attribute — correct

# _suites.py (imported once, at process start)
from ._common import _COVERAGE_MODE   # binds a LOCAL name to the CURRENT value: False
...
if _COVERAGE_MODE: ...   # always reads the frozen False, never sees _cli.py's later True
```

Because `run_all_frontend_tests()` never saw `_COVERAGE_MODE = True`, it never set the
`COVERAGE_BACKEND=1` environment variable before launching the Playwright subprocess, so
`playwright.config.ts`'s `webServer` command never wrapped the dev server with
`coverage run -m uvicorn`, and no `.coverage.*` fragments existed to combine at the end of the
run.

## Solution

Applied the identical fix pattern as `_RESUME_MODE`: removed `_COVERAGE_MODE` from the
`from ._common import (...)` block in `_suites.py`, added `from . import _common`, and changed
all 3 usage sites to reference `_common._COVERAGE_MODE` (module-attribute access, evaluated
fresh at call time) instead of the stale local name.

## Prevention

Same lesson as [[problems/resume-mode-stale-import]]: never import a **mutable global flag**
with `from module import name` if another module sets it later via `module.name = x`. This is
now the *second* occurrence of this exact anti-pattern in `scripts/test_runner/` — worth a
grep sweep (`grep -rn "^from \._common import" scripts/test_runner/`) whenever a new global
flag is added to `_common.py`, to confirm every consumer uses attribute access instead of a
direct name import.

## Verification

Confirmed via a monkeypatched-`subprocess.run` throwaway script that intercepted all Playwright
subprocess launches during a `--coverage` run: before the fix, 0/47 calls received
`COVERAGE_BACKEND=1`; after the fix, all 47 did. Re-ran the full
`./dev.py test --coverage --fresh-run all` suite end-to-end (14/14 categories passed) and
confirmed `.coverage_data/frontend` and `htmlcov-frontend/` were created for the first time.

## Source files

| Role | Path |
|------|------|
| Definition | `scripts/test_runner/_common.py` |
| Correct pattern (unaffected) | `scripts/test_runner/_cli.py` (`_common._COVERAGE_MODE` attribute access) |
| Fixed | `scripts/test_runner/_suites.py` (`run_all_tests`, `run_all_backend_tests`, `run_all_frontend_tests`) |
| Consumer (env var) | `frontend/playwright.config.ts` (`webServer` command reads `COVERAGE_BACKEND`) |
