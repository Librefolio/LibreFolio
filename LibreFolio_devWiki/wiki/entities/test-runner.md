---
title: "Test Runner (scripts/test_runner package)"
category: entity
type: module
tags: [testing, infrastructure, cli, test-runner, registry-pattern, coverage, parallelism, scripts]
related:
  - entities/devpy-cli
  - decisions/test-runner-package-split
  - concepts/test-isolation-classes
  - concepts/derived-test-inventory
  - concepts/run-cache-and-campaign-semantics
  - concepts/unique-test-identifiers
  - problems/registered-but-unreachable-test-actions
  - problems/env-var-injection-point-duplicated
---

# Test Runner

> **Rewritten 2026-09-01 against the tree.** The previous version of this page was
> integrally false: it documented `_orchestrator.py`, `_backend_unit.py`, `_e2e.py`,
> a `suites/` directory, a `@registry.register("transactions")` decorator with
> auto-discovery, and a CLI shaped `./dev.py test backend --suite transactions`.
> **None of that exists, and none of it ever did.** It was written from a plan, not
> from the code. Everything below was verified against `scripts/test_runner/` on
> 2026-09-01.

## Role

`scripts/test_runner/` is the test orchestration package behind `./dev.py test`.
It owns a **catalogue** of every runnable test action, decides what a suite name
expands to, schedules units across workers according to their isolation class,
launches pytest and Playwright, and consolidates coverage.

It is infrastructure used every working day, and it is the single place where
"what does the project actually test?" has an answer.

## Location

`scripts/test_runner/` — **30 Python modules, ~9 500 lines**, flat layout.
There is **no** subpackage: no `actions/`, no `suites/`, no `providers/`.

```
scripts/test_runner/
├── __init__.py            # package facade
├── __main__.py            # python -m scripts.test_runner
├── _registry.py     (41)  # TEST_REGISTRY assembly — the spine
├── _common.py      (632)  # globals, run_command, pytest cmd builder, add_test()
├── _cli.py       (1 264)  # argparse tree + dispatch + check-orphans
├── _suites.py      (221)  # run_all_tests / _backend / _frontend
├── _inventory.py   (386)  # derived inventory, isolation classifier, reachability
├── _scheduler.py   (145)  # balance(), plan(), resolve_workers()
├── _executor.py    (267)  # worker groups, per-worker env, coverage combine
├── _consolidate.py (380)  # one Playwright invocation per category
├── _consolidate_backend.py (295)  # one pytest invocation per category
├── _server.py      (367)  # one shared test server for the whole run
├── _run_cache.py   (225)  # --resume / --fresh-run / --run-status state
├── _coverage.py    (408)  # coverage finalisation and reporting
├── _archive.py     (228)  # 00_archive/<YYYYMMDD_HHMM>.<ext> convention
├── _backend_api.py       _backend_db.py       _backend_external.py
├── _backend_schemas.py   _backend_services.py _backend_utils.py
├── _frontend_common.py   _frontend_ai_export.py _frontend_asset.py
├── _frontend_broker.py   _frontend_fx.py       _frontend_portfolio.py
├── _frontend_transaction.py _frontend_user.py  _frontend_utility.py
```

## Key interfaces

### The registry is explicit, not auto-discovered

`_registry.py` is 41 lines and does exactly one thing: it imports **14
`populate_registry` functions** — one per category module — and calls them in a
declared order on a single `TEST_REGISTRY` dict.

```python
from ._backend_api import populate_registry as _pop_api  # registers "api" + "e2e"
...
TEST_REGISTRY: dict = {}
_pop_external(TEST_REGISTRY)
_pop_db(TEST_REGISTRY)
...
_pop_front_ai_export(TEST_REGISTRY)
```

> Order matters: it determines the order in CLI help and in the `all` suites.

There is **no decorator, no import-time side effect, no auto-discovery**. Adding a
category is two edits: a module with a `populate_registry`, and a line in
`_registry.py`. That is the whole extension point — and it was chosen deliberately
(see [[decisions/test-runner-package-split]]).

### 15 categories

14 `populate_registry` calls produce **15 registry keys**, because
`_backend_api.populate_registry` registers both `api` and `e2e`:

| backend | frontend |
|---|---|
| `external`, `db`, `services`, `utils`, `schemas`, `api`, `e2e` | `front-utility`, `front-broker`, `front-user`, `front-fx`, `front-asset`, `front-transaction`, `front-portfolio`, `front-ai-export` |

### Actions are declared with `add_test()`

Each category module builds its dict by calling `_common.add_test()` — **250 call
sites across the package**. The signature is the real contract of the runner:

```python
add_test(category, action, func, *, name, desc,
         prereq=None, tests=None, note=None, in_all=True,
         isolation=None, exclusive_because=None)
```

`isolation` and `exclusive_because` are what make the scheduler possible
(see [[concepts/test-isolation-classes]]); `in_all` is what makes an action
reachable from an `all` suite (see [[concepts/derived-test-inventory]]).

### CLI

The shape is `./dev.py test <categoria> <azione>` — category first, then action,
both as **subcommands**, not as `--suite` flags:

```bash
./dev.py test all
./dev.py test all-backend
./dev.py test all-frontend
./dev.py test services
./dev.py test front-transaction
./dev.py test check-orphans
```

Category subparsers are generated from `TEST_REGISTRY.keys()` in
`_cli.py` (~L471-500); the fixed extras (`all`, `all-backend`, `all-frontend`,
`check-orphans`, coverage) are added by hand right after. Run-wide flags live on
the `test` parser itself: `--workers`, `--coverage`, `--resume`, `--fresh-run`,
`--run-status`, `--fail-fast`, `--no-consolidate`, `--log-dir`, `--no-shared-server`,
`--assume-scoped`.

## Design notes

Four mechanisms carry most of the weight, and each has its own concept page —
they are **not** repeated here:

| Mechanism | Where it lives | Page |
|---|---|---|
| Isolation classes (`pure` / `read` / `write-scoped` / `write-global`) drive what may run in parallel | `_inventory.py`, `_scheduler.py` | [[concepts/test-isolation-classes]] |
| The `all` lists are **derived** from the registry, not hand-written | `_common.py` `_get_category_tests_for_all()` | [[concepts/derived-test-inventory]] |
| Run cache and what "a campaign" means across invocations | `_run_cache.py` | [[concepts/run-cache-and-campaign-semantics]] |
| Unique test identifiers (`unique_id()`) and what they do *not* guarantee | `backend/test_scripts/test_utils.py` | [[concepts/unique-test-identifiers]] |

Two further design choices are worth naming here because they are the runner's
main performance levers:

- **One shared server for the whole run** (`_server.py`). Before it, every
  `test_api` module started its own uvicorn — the FastAPI app was imported 47
  times per run, measured at ~11 of the 15 minutes those invocations cost, and it
  made the modules mutually exclusive by construction.
- **Consolidation** (`_consolidate.py`, `_consolidate_backend.py`). One invocation
  per *category* instead of one per action. Backend: the fixed cost of a
  `pipenv run python -m pytest <file>` is measured at **2,6 s**. Frontend: a
  per-action run pays a populate, eight user creations, a Playwright `globalSetup`
  that populates and creates users *again*, and a webServer start/stop —
  roughly eleven cold Python starts per spec file. `--no-consolidate` is the escape
  hatch back to per-action runs.

### Known failure shapes

Both known runner failures share one shape — a registered thing that does nothing
and does not say so ([[concepts/silent-no-op-option]]):

- [[problems/registered-but-unreachable-test-actions]] — 6 actions / ~273 tests
  registered, green, and reached by no suite.
- [[problems/env-var-injection-point-duplicated]] — `E2E_WORKERS` reached one of
  two Playwright launchers; the other silently used the default.

## History

| Date | Change |
|------|--------|
| 2026-06 (Phase 07) | Monolithic `scripts/test_runner/` (4 841 lines) split into a package — see [[decisions/test-runner-package-split]] |
| 2026-08 (P8) | Parallel execution model: isolation classes, scheduler, executor — see [[sources/p8-runner-parallel-architecture]] |
| 2026-08-29 | `check-orphans` rewritten to prove reachability; `all` lists derived from the registry |
| 2026-09-01 | **This page rewritten from the code**; the previous description was fabricated |

## Source files

| Role | Path |
|------|------|
| Package facade | `scripts/test_runner/__init__.py` |
| Registry assembly (14 `populate_registry`) | `scripts/test_runner/_registry.py` |
| `add_test()`, `_get_category_tests_for_all()` | `scripts/test_runner/_common.py` |
| CLI tree + dispatch + `check-orphans` | `scripts/test_runner/_cli.py` |
| `all` / `all-backend` / `all-frontend` | `scripts/test_runner/_suites.py` |
| Derived inventory + isolation classifier | `scripts/test_runner/_inventory.py` |
| Scheduler | `scripts/test_runner/_scheduler.py` |
| Parallel executor | `scripts/test_runner/_executor.py` |
| Shared test server | `scripts/test_runner/_server.py` |
| Frontend consolidation | `scripts/test_runner/_consolidate.py` |
| Backend consolidation | `scripts/test_runner/_consolidate_backend.py` |
| Run cache | `scripts/test_runner/_run_cache.py` |
| Coverage finalisation | `scripts/test_runner/_coverage.py` |
| Artefact archiving | `scripts/test_runner/_archive.py` |
| mkdocs (runner architecture) | `mkdocs_src/docs/developer/test-walkthrough/runner_architecture.md` |
| mkdocs (test walkthrough index) | `mkdocs_src/docs/developer/test-walkthrough/index.md` |
| dev.py integration | `dev.py` |
