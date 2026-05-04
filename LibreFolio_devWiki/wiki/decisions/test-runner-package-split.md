---
title: "Test Runner: monolith → 18-module package"
category: decision
status: resolved
date: 2026-05-26
tags: [testing, infrastructure, cli, refactoring, test_runner, pytest, playwright]
related: [entities/devpy-cli, concepts/backend-test-isolation, concepts/e2e-data-testid-rule]
---

# Decision: Test Runner monolith → 18-module package

## Context

`scripts/test_runner.py` had grown to **4841 lines in a single file**. It defined every test category, every test action (~115 total across 12 categories), the CLI parsers, the registry data structure, coverage helpers, suite runners, and shared utilities — all in one place.

Pain points:
- **Navigation**: impossible to jump to a specific test category without excessive scrolling.
- **Merge conflicts**: any two branches touching test infrastructure would collide.
- **Cognitive load**: contributors had to understand the full file to add a single test.
- **No locality**: registry metadata was hundreds of lines away from the functions it described.

## Options Considered

1. **Keep single file, add region comments** — low effort, doesn't solve merge conflicts or locality.
2. **Split into package with distributed registry** — each module owns its tests and registry data; a thin assembler imports them. More files, but each is self-contained.
3. **Plugin-based auto-discovery** — use `importlib` entry points or directory scanning. Over-engineered for an internal test harness.

## Decision

**Option 2: Split into an 18-module package at `scripts/test_runner/`** with a distributed registry pattern.

### New architecture

```
scripts/test_runner/           # Package (was single file)
├── __init__.py               # Re-exports: _ensure_test_users, register_subparser, TEST_REGISTRY
├── __main__.py               # Entry point for python -m scripts.test_runner
├── _common.py (272 lines)    # Globals, _run_test_suite, run_command, _build_pytest_cmd,
│                             #   registry builder helpers (make_category, add_test)
├── _backend_external.py      # external_* test functions + provider discovery (regex-based)
├── _backend_db.py            # db_* test functions (create, validate, populate, fx-rates, brim, etc.)
├── _backend_services.py      # services_* test functions (21 actions)
├── _backend_utils.py         # utils_* test functions
├── _backend_schemas.py       # schemas_* test functions
├── _backend_api.py           # api_* + e2e_* test functions (biggest: 500 lines,
│                             #   registers both "api" and "e2e" categories)
├── _frontend_common.py       # _ensure_frontend_build, _ensure_db_populated,
│                             #   _ensure_test_users, _run_playwright, _list_front_tests,
│                             #   _list_pytest_tests
├── _frontend_utility.py      # Auth, settings, files, select, image-crop E2E tests
├── _frontend_user.py         # Brokers, multi-user, broker-sharing E2E tests
├── _frontend_fx.py           # FX unit (Vitest) + E2E tests
├── _frontend_asset.py        # Asset E2E tests
├── _frontend_transaction.py  # Transaction E2E tests (NEW category)
├── _registry.py (35 lines)   # Assembles TEST_REGISTRY by calling populate_registry() from each module
├── _suites.py                # run_all_tests, run_all_backend_tests, run_all_frontend_tests,
│                             #   _BACKEND_CATEGORIES, _FRONTEND_CATEGORIES
├── _coverage.py              # Coverage finalization, _handle_coverage_command,
│                             #   _coverage_show, _coverage_combine
└── _cli.py (481 lines)       # Parsers, dispatch, main(), register_subparser (for dev.py integration)
```

### Distributed Registry Pattern

Each domain module defines a `populate_registry(registry: dict)` function that uses two helpers from `_common.py`:

- **`make_category(help_text, description)`** → creates the `_meta` dict for a category.
- **`add_test(category, action, func, *, test_names=True, name, desc, prereq=None, tests=None, note=None)`** → registers a single test action.

The assembler (`_registry.py`, 35 lines) imports all `populate_registry` functions and calls them in order. This keeps registry data **next to the test functions it describes** (locality principle).

### Category constants

In `_suites.py`:
```python
_BACKEND_CATEGORIES = ("external", "db", "services", "utils", "schemas", "api", "e2e")
_FRONTEND_CATEGORIES = ("front-utility", "front-user", "front-fx", "front-asset", "front-transaction")
```

**Total: 12 categories, ~115 test actions registered.**

### Adding a new test category

Only 3 touches required:

1. Create `_frontend_newcategory.py` with test functions + `populate_registry()`.
2. Add one import line in `_registry.py`.
3. Add the category name to `_FRONTEND_CATEGORIES` in `_suites.py`.

## Consequences

### Gains
- **Largest file is 500 lines** (`_backend_api.py`), average ~200 lines. Previously 4841 lines.
- **Merge conflicts minimized** — parallel work on different test categories touches different files.
- **Locality** — registry metadata lives in the same file as the functions it describes.
- **Each module is independently testable** and self-contained.
- **Backward compatibility preserved** — `dev.py` imports `from scripts.test_runner import _ensure_test_users, register_subparser` via `__init__.py` re-exports.

### Trade-offs
- 18 files instead of 1 — mitigated by clear naming convention (`_backend_*.py`, `_frontend_*.py`).
- Import chain: `__init__.py` → `_registry.py` → all modules. Startup cost negligible for a CLI tool.

### Fixes included in this refactoring
- **`_build_pytest_cmd` consistency**: 4 functions were manually building pytest commands with `[*pipenv_prefix(), "python", "-m", "pytest", ...]` instead of using the shared `_build_pytest_cmd()` helper. All now use the helper.
- **`front-transaction` category**: new category added as part of this split. Maps to `frontend/e2e/transactions/transactions.spec.ts`. Run with `./dev.py test front-transaction transactions --ui`.

## Source files

| Role | Path |
|------|------|
| Package root | `scripts/test_runner/__init__.py` |
| Entry point | `scripts/test_runner/__main__.py` |
| Shared helpers | `scripts/test_runner/_common.py` |
| Registry assembler | `scripts/test_runner/_registry.py` |
| Suite runners | `scripts/test_runner/_suites.py` |
| CLI & parsers | `scripts/test_runner/_cli.py` |
| Coverage | `scripts/test_runner/_coverage.py` |
| Backend: external | `scripts/test_runner/_backend_external.py` |
| Backend: db | `scripts/test_runner/_backend_db.py` |
| Backend: services | `scripts/test_runner/_backend_services.py` |
| Backend: utils | `scripts/test_runner/_backend_utils.py` |
| Backend: schemas | `scripts/test_runner/_backend_schemas.py` |
| Backend: api + e2e | `scripts/test_runner/_backend_api.py` |
| Frontend: common | `scripts/test_runner/_frontend_common.py` |
| Frontend: utility | `scripts/test_runner/_frontend_utility.py` |
| Frontend: user | `scripts/test_runner/_frontend_user.py` |
| Frontend: fx | `scripts/test_runner/_frontend_fx.py` |
| Frontend: asset | `scripts/test_runner/_frontend_asset.py` |
| Frontend: transaction | `scripts/test_runner/_frontend_transaction.py` |
| dev.py integration | `dev.py` |

