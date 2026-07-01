---
title: "Test Runner (modular package)"
category: entity
type: module
tags: [testing, infrastructure, cli, test-runner, registry-pattern, coverage, modular, scripts]
related:
  - entities/devpy-cli
  - decisions/test-runner-package-split
  - concepts/backend-test-isolation
---

# Test Runner

## Role

The test orchestration package that coordinates all LibreFolio test suites (backend API, backend unit, frontend E2E) via a unified CLI interface. It implements a distributed registry pattern where each test suite module self-registers, enabling decoupled orchestration without a central hardcoded list.

> **Note**: Was previously a monolithic `test_runner.py` (4841 lines). Refactored to a 18-module package in Phase 07 (see [[decisions/test-runner-package-split]]). References to `test_runner.py` in older docs are **stale** — the file no longer exists.

## Location

`scripts/test_runner/` (package directory)

```
scripts/test_runner/
├── __init__.py
├── _cli.py          # CLI entry point (argparse)
├── _registry.py     # Suite registry (distributed registration)
├── _orchestrator.py # Top-level orchestration
├── _backend_api.py  # Backend API test runner
├── _backend_unit.py # Backend unit test runner
├── _e2e.py          # Playwright E2E runner
├── _coverage.py     # Coverage data swap-in/swap-out logic
└── suites/          # Per-suite modules (self-register via registry)
    ├── transactions.py
    ├── assets.py
    ├── fx.py
    └── ...
```

## Key Interfaces

### Registry Pattern

Each suite module calls `registry.register(suite_name, run_fn)` at module import time. The orchestrator discovers suites by importing the `suites/` package — no hardcoded list required.

```python
# Example suite module
from scripts.test_runner._registry import registry

@registry.register("transactions")
def run_transactions_suite(args):
    ...
```

### Coverage Swap-In/Swap-Out

The runner manages `.coverage` file swap-in/swap-out to enable coverage isolation between suite runs and aggregate coverage across multiple runs. This mechanism is documented in `test-walkthrough/index.md`.

### CLI via `dev.py`

```bash
./dev.py test backend --suite transactions
./dev.py test frontend --spec e2e/transactions/
./dev.py test all
```

## History

| Date | Change |
|------|--------|
| Phase 07 | Monolithic `scripts/test_runner.py` (4841 lines) → 18-module package (see [[decisions/test-runner-package-split]]) |
| 2026-06-18 | Documentation updated: `test-walkthrough/index.md` updated to reference `scripts/test_runner/`; new `runner_architecture.md` written |
| 2026-06-18 | Mermaid diagrams updated to ELK layout |

## Source files

| Role | Path |
|------|------|
| Package root | `scripts/test_runner/__init__.py` |
| CLI | `scripts/test_runner/_cli.py` |
| Registry | `scripts/test_runner/_registry.py` |
| Orchestrator | `scripts/test_runner/_orchestrator.py` |
| Coverage | `scripts/test_runner/_coverage.py` |
| mkdocs (test walkthrough) | `mkdocs_src/docs/developer/test-walkthrough/index.md` |
| mkdocs (runner architecture) | `mkdocs_src/docs/developer/test-walkthrough/runner_architecture.md` |
| dev.py integration | `dev.py` (test subcommand) |
