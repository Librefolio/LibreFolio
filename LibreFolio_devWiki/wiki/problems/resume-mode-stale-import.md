---
title: "Test runner --resume never skipped already-passed sub-suites (stale _RESUME_MODE import)"
category: problem
status: resolved
date: 2026-07-13
tags: [testing, test-runner, python, infra]
related: []
---

# Problem: `--resume` Re-Ran Every Sub-Suite Inside a Category

## Summary

`./dev.py test --resume all` correctly skipped whole *categories* that had already passed
(e.g. `All Broker Tests`), matching `scripts/test_runner/.run_cache.json`. But once a category
had to run at all (because it previously failed partway through), it always re-ran **every**
sub-suite inside it from the beginning — including ones the cache already recorded as passed —
instead of resuming from the actual failure point. Root cause: 13 of the `scripts/test_runner/
_*.py` modules imported the resume flag with `from ._common import _RESUME_MODE`, which binds
a local name to the value `_RESUME_MODE` had *at import time* (`False`, `_common.py`'s
default). `_cli.py` later does `_common._RESUME_MODE = True` — a mutation of the `_common`
module's own attribute — which never updates the already-bound local copies in the 13 files
that imported the name directly.

## Root Cause (classic Python `from x import y` gotcha)

```python
# _common.py
_RESUME_MODE = False  # default

# _cli.py (runs after argparse)
_common._RESUME_MODE = resume  # mutates the attribute on the module object — correct

# _frontend_transaction.py (imported once, at process start)
from ._common import _RESUME_MODE   # binds a LOCAL name to the CURRENT value: False
...
resume=_RESUME_MODE   # always reads the frozen `False`, never sees _cli.py's later True
```

`_cli.py` itself avoids the trap for the top-level "Complete Test Suite" call by passing
`resume=_common._RESUME_MODE` (attribute access, always fresh) directly as a function
argument — so category-level skipping worked. But every category's own internal `..._all()`
function used the stale imported name for its *nested* `_run_test_suite(..., resume=...)`
call, so nested resume was silently broken everywhere.

## Solution

Removed `_RESUME_MODE` from the `from ._common import (...)` blocks in all 13 affected files,
added `from . import _common`, and changed every `resume=_RESUME_MODE` call site to
`resume=_common._RESUME_MODE` (attribute access on the module, evaluated fresh at call time).

## Prevention

Never import a **mutable global flag** with `from module import name` if another module sets
it later via `module.name = x`. Either import the module itself (`from . import module`) and
access `module.name`, or expose a getter function (`def is_resume(): return _RESUME_MODE`).

## Verification

Confirmed via `--run-status` + a full `--resume all` run: after the fix, a category that
failed partway (e.g. Transaction Tests, stopped at `TX Bulk Suggest UX`) correctly printed
`⏩ SKIP (cached pass)` for all 11 already-passed sub-suites and resumed exactly at the failed
one, instead of re-running ~15 minutes of already-green Playwright specs.

## Source files

| Role | Path |
|------|------|
| Correct pattern (unaffected) | `scripts/test_runner/_cli.py` (`_common._RESUME_MODE` attribute access) |
| Definition | `scripts/test_runner/_common.py:31` |
| Fixed (13 files) | `scripts/test_runner/_backend_api.py`, `_backend_db.py`, `_backend_external.py`, `_backend_schemas.py`, `_backend_services.py`, `_backend_utils.py`, `_frontend_asset.py`, `_frontend_broker.py`, `_frontend_fx.py`, `_frontend_portfolio.py`, `_frontend_transaction.py`, `_frontend_user.py`, `_frontend_utility.py` |
