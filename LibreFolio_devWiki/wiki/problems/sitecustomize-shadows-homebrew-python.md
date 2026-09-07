---
title: "Custom sitecustomize.py on PYTHONPATH shadows Homebrew Python's own — pipenv breaks"
category: problem
date: 2026-09-03
tags: [testing, coverage, macos, homebrew, python, environment]
related:
  - concepts/test-runner-architecture
---

# Problem: a project sitecustomize.py on PYTHONPATH silently breaks Homebrew Python

## Summary

Adding a directory containing a `sitecustomize.py` to `PYTHONPATH` (the standard
coverage.py recipe for measuring `multiprocessing spawn` children, P1-13) made the
shared test backend die at bootstrap with exit code 1. The visible failure was the
frontend build aborting on the strict JS-cache check (I1), but the root cause was two
layers deeper: every `pipenv run …` child was dying with `ModuleNotFoundError: No
module named 'pipenv'`.

## Root cause

Python imports **exactly one** `sitecustomize` module at startup — the first found on
`sys.path`. Homebrew Python ships its own `sitecustomize.py`
(`/opt/homebrew/opt/python@3.14/Frameworks/.../lib/python3.14/sitecustomize.py`) which
rewrites `sys.prefix` from the Cellar path to the opt prefix and adds
`/opt/homebrew/lib/python3.14/site-packages` — where brew-installed Python packages
like `pipenv` live.

Our `_coverage_sitecustomize/sitecustomize.py`, prepended via `PYTHONPATH`, **shadowed
Homebrew's**: prefix never fixed → pipenv's module invisible → every pipenv subprocess
spawned by the server flow (`dev.py server` → pipenv → coverage → uvicorn) crashed.

Two traps on top:

1. The failure only surfaces through a *fail-loud* consumer. Before I1 made the JS-cache
   check strict, the broken pipenv call was a silent warning.
2. When `COVERAGE_PROCESS_START` is set, the unguarded `import coverage` also raises on
   interpreters along the exec chain that have no coverage installed (the Homebrew
   Python hosting the pipenv launcher) — that exception aborts the whole sitecustomize,
   including any chaining logic written after it.

## Fix (in `backend/test_scripts/_coverage_sitecustomize/sitecustomize.py`)

1. `import coverage` is wrapped in `try/except ModuleNotFoundError` — interpreters
   without coverage are not measurement targets, let them pass.
2. **Chain-exec the shadowed sitecustomize**: after the coverage block, scan `sys.path`
   for another `sitecustomize.py` outside our own directory and `exec` it in our
   namespace. Homebrew's prefix fixup then runs as designed; on interpreters without
   their own sitecustomize (the venv) the scan is a no-op.

## Verification

- `PYTHONPATH=<dir> pipenv --version` works again (was: `ModuleNotFoundError`).
- With `COVERAGE_PROCESS_START` set, venv children still write `.coverage.<host>.<pid>`
  files (spawn-worker coverage works).
- Faithful runner repro: `./dev.py server --test --coverage` boots to health 200.

## Lesson

Any time a project puts a `sitecustomize.py` on `PYTHONPATH`, it must chain to the
interpreter's own one — on Homebrew Python (macOS dev machines) that file is
load-bearing for *prefix resolution*, not just convenience. `usercustomize.py` is not
an alternative: it is not imported inside virtualenvs (user site disabled), which is
exactly where spawn children run.

## Source files

| File | Role |
| --- | --- |
| `backend/test_scripts/_coverage_sitecustomize/sitecustomize.py` | The fixed file (chain-exec + guarded import) |
| `scripts/test_runner/_common.py` | `apply_subprocess_coverage_env` — sets COVERAGE_PROCESS_START + PYTHONPATH |
