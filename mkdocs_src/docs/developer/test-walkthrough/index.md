# 🧪 Test Walkthrough

This section guides you through the LibreFolio test suite. Understanding the tests is one of the best ways to understand the codebase.

!!! note "Modular Test Runner Architecture"

    LibreFolio uses a modular test orchestrator package located in `scripts/test_runner/` to manage, register, and isolate coverage for all backend and frontend test suites. For details on how the runner is structured and how to extend it, see the [Test Runner Architecture](runner_architecture.md) documentation.


## 🚀 Running Tests

All tests are executed through `dev.py`:

```bash
# Run everything
./dev.py test all

# Run a single category
./dev.py test api all

# Run one action (here: backend/test_scripts/test_api/test_auth_api.py)
./dev.py test api auth

# Run only the tests whose name matches (pytest -k)
./dev.py test api auth test_register_success

# List available tests (without running them)
./dev.py test api all --list
```

The action is required, `--list` included: `all` lists the whole category, an action name narrows
the list to that action (on a backend category, to the first test file the action runs). On a
backend category `--list` runs `pytest --collect-only` and prints the test names grouped by file and
class; on a frontend category it prints the `test.describe()` and `test()` titles of the category's
Playwright spec files (Vitest files are not listed).

### 🌐 Global Flags

| Flag | Description |
|------|-------------|
| `-q` / `--quiet` | Suppress the detailed test output. Without it, the output is verbose |
| `--coverage [py\|js\|all]` | Run with code coverage tracking. The language is optional and defaults to `all` |
| `--cov-clean-backend` | Together with `--coverage`, clean Python coverage from backend tests (`htmlcov-backend/` + `.coverage_data/backend`) |
| `--cov-clean-backend-e2e` | Together with `--coverage`, clean Python coverage collected during E2E runs (`htmlcov-backend-e2e/` + `.coverage_data/frontend`) |
| `--cov-clean-js` | Clean JS/Svelte coverage (`coverage-js/`). Manual utility only — a `--coverage js` run cleans it by itself |
| `--workers N\|auto` | Run isolation-safe backend units in parallel; the same number sets the Playwright workers, capped at half the logical cores. Default `1` — the serial path, unchanged. `auto` is half the cores |
| `--fail-fast` | Stop handing out work after the first red. The default runs everything and reports every failure |
| `--resume` | Continue from the last failure: skip the tests the run cache records as passed and run the rest (see *Run cache and timing campaign* below) |
| `--fresh-run` | Delete the run cache before starting, and open a new timing campaign. Without a category it only deletes the cache |
| `--run-status` | Print the run cache (per suite, the tests passed and where the last run stopped) and exit without running anything |
| `--log-file PATH` | Tee the full run output (build, pytest and Playwright output included) to `PATH` while still printing it. An existing file is overwritten |
| `--log-dir PATH` | One log file per test unit. Defaults to `.testLog`; `--log-dir ""` turns it off |
| `--no-consolidate` | Keep one invocation per action. By default a whole category or suite is grouped: one pytest invocation per backend category (`db` and `external` keep one per action) and, per frontend category, one vitest run plus one Playwright run per project selection (desktop only, or desktop and mobile), split into batches of 8 specs under JS coverage |
| `--no-shared-server` | Do not start the one test backend the run shares: each pytest process and each Playwright run that needs a server starts its own, and the `--workers` parallel pass keeps only the units that touch neither database nor server. Slower — an escape hatch |
| `--assume-scoped` | Experiment for the `--workers` parallel pass of backend categories: every pytest unit counts as parallel-safe, whatever isolation class the catalogue gives it, except the units with a written `exclusive_because`. No effect at one worker or with `--no-shared-server`. The reds are the work list, not a regression |
| `--test-port PORT` / `--port PORT` | Port of this run's test backend. Defaults to `TEST_PORT`, then `6041` — see [Isolated Runtime Lanes](#isolated-runtime-lanes) |
| `--data-dir PATH` | Test data root of this run. Defaults to `LIBREFOLIO_TEST_DATA_DIR`, then `backend/data/test` — see [Isolated Runtime Lanes](#isolated-runtime-lanes) |

!!! note "Where the flags go"

    They belong to `./dev.py test`, so they come **before** the category:
    `./dev.py test --workers 4 --coverage py services all`.

!!! warning "`--cov-clean-frontend` is deprecated"

    It still works as an alias for `--cov-clean-backend-e2e`, but the old name was
    misleading: it never cleaned JavaScript coverage. It cleans the **Python**
    coverage collected while Playwright drives the backend.

    JS coverage has no accumulate-or-clean choice to make. It is raw V8 data whose
    byte offsets only mean anything for the bundle that produced them, so it cannot
    survive a frontend rebuild — a `--coverage js|all` run therefore always wipes it
    first. `--cov-clean-js` exists only to clean it outside a run.

!!! tip "Two axes, not one"

    `--coverage` selects **which language** is measured; the suite you run selects
    **which tests drive it**. See [Coverage Model](coverage-model.md) for the full
    picture — including why the report formerly called `htmlcov-frontend/` actually
    measured Python.

!!! note "Run cache and timing campaign"

    The serial suites and the consolidated passes record their outcomes in
    `scripts/test_runner/.run_cache.json` (gitignored): per suite, the tests that passed and
    the last one that failed. `--resume` skips the recorded passes, `--run-status` summarises the
    file, `--fresh-run` deletes it. A serial suite that passes in full drops its own entry; the
    consolidated passes keep theirs (`consolidated:<category>`) until the next `--fresh-run`.
    The `--workers` parallel pass neither reads nor writes the cache, so a `--resume` runs its
    units again.

    A second gitignored file, `scripts/test_runner/.campaign.json`, times the *campaign*: the
    run that a `--fresh-run` opens and every run after it. Each run of a category or suite
    closes with a **Timing** section: this invocation's duration, the wall-clock time since the
    campaign opened (the gaps where fixes were written included) and, once the campaign holds
    several invocations, their count and summed machine time.

### 🛣️ Isolated Runtime Lanes

A test run owns one **runtime lane**: the port of the backend it starts and talks to, and
the data directory that backend uses (`sqlite/app.db`, uploads, broker reports, logs). Runs
that are active at the same time — one per worktree — must each have their own lane: never
point two active runs at the same port or the same data directory.

| Flag | Environment variable | Default | Lane resource |
|------|----------------------|---------|---------------|
| `--test-port PORT` / `--port PORT` | `TEST_PORT` | `6041` | Port of the test backend |
| `--data-dir PATH` | `LIBREFOLIO_TEST_DATA_DIR` | `backend/data/test` | Root of the test data |

A flag wins over the shell environment, which wins over the checkout's `.env`. A relative
data path resolves against the root of the checkout that runs the command, so each worktree's
default data directory is already its own. The port is machine-wide, so every worktree that
runs tests at the same time needs a different one — on the command line, or as `TEST_PORT` in
that worktree's `.env`. If you set `LIBREFOLIO_TEST_DATA_DIR` to an absolute path, give each
worktree a different one as well.

```bash
# A second worktree, testing while another one uses the default lane (6041)
./dev.py test --test-port 6141 api all
```

The runner applies the lane before any setup, server start, or child process
(`configure_test_runtime` in `scripts/cli_base.py`), and stops with an error when:

- the port is outside 1–65535 or equals the production port (`PORT`, default `6040`);
- the data directory overlaps the production data directory (`backend/data/prod`, or
  `LIBREFOLIO_DATA_DIR`) in either direction, sits inside — or holds in its managed
  subdirectories — a directory marked as production data, or has a managed path that
  escapes it or aliases production data.

The resolved `TEST_PORT` and `LIBREFOLIO_TEST_DATA_DIR` are exported to every child process,
together with a random lane identity (`LIBREFOLIO_TEST_LANE_ID`). A backend counts as ready
only when `/api/v1/system/test-lane-health` echoes that identity in the
`X-LibreFolio-Test-Lane` header, and the shared test server refuses to start on a port that
another process already holds: it never reuses or terminates another lane's server. The
contract is covered by `./dev.py test utils runtime-isolation`.

### 🔍 Provider Filter Flags (external, all, all-backend)

| Flag | Description |
|------|-------------|
| `--providers CODE [CODE ...]` | Only test these provider(s) |
| `--exclude-providers CODE [CODE ...]` | Exclude these provider(s) from testing |

```bash
# Skip yfinance when Yahoo Finance is down
./dev.py test external asset-providers --exclude-providers yfinance

# The same flags work with all and all-backend
./dev.py test all --exclude-providers yfinance
./dev.py test all-backend --providers ECB justetf
```

!!! tip "See available provider codes"

    Run `./dev.py test external -h` to see all available provider codes (Asset, FX, BRIM), dynamically discovered from the source tree.

### 🖥️ Frontend Flags

Frontend test categories support additional flags (`--headed`, `--debug`, `--ui`). See the [Frontend Tests Overview](front-overview.md) for details.

---

## 📋 Test Categories

LibreFolio organizes tests into **15 categories** — seven backend, eight frontend — grouped by layer:

| Category | Command | What It Tests |
|----------|---------|---------------|
| **External** | `./dev.py test external all` | Provider integrations (FX, assets, BRIM) — no server needed |
| **Database** | `./dev.py test db all` | SQLite schema, migrations, constraints, persistence — no server needed |
| **Services** | `./dev.py test services all` | Business logic in the service layer |
| **Utils** | `./dev.py test utils all` | Helper functions and utility modules |
| **Schemas** | `./dev.py test schemas all` | Pydantic model validation |
| **API** | `./dev.py test api all` | FastAPI endpoints (auto-starts server) |
| **E2E** | `./dev.py test e2e all` | Backend end-to-end with API interaction |
| **Front-Utility** | `./dev.py test front-utility all` | Auth, settings, files, select, image crop, onboarding, layout, scheduler (Playwright) + core and component units (Vitest) |
| **Front-Broker** | `./dev.py test front-broker all` | Broker list, CRUD, detail page, deletion recovery (Playwright) + broker helpers (Vitest) |
| **Front-User** | `./dev.py test front-user all` | Multi-user isolation, broker sharing (Playwright) + auth and client-session stores (Vitest) |
| **Front-FX** | `./dev.py test front-fx all` | FX list, detail, add-pair, editor, CSV import, sync, bulk actions (Playwright) + EditBuffer, TimeSeriesStore, fxStoreRegistry (Vitest) |
| **Front-Asset** | `./dev.py test front-asset all` | Asset list, detail, modal, data editor, merge, classification (Playwright) + price store, chart aggregation (Vitest) |
| **Front-Transaction** | `./dev.py test front-transaction all` | Transaction modals, table, bulk operations, WAC, import wizard (Playwright) + payload and commit helpers (Vitest) |
| **Front-Portfolio** | `./dev.py test front-portfolio all` | Dashboard charts, banners, page cache, privacy masking, risk analysis (Playwright) + portfolio and risk stores (Vitest) |
| **Front-AI-Export** | `./dev.py test front-ai-export all` | AI Export panel, catalog, session memory, contracts (Playwright) + AI Export and signal units (Vitest) |

### 🏃 Meta Categories

| Meta Category | Command | What It Runs |
|---------------|---------|--------------|
| **All** | `./dev.py test all` | All backend + frontend tests |
| **All Backend** | `./dev.py test all-backend` | All backend tests (external → e2e) |
| **All Frontend** | `./dev.py test all-frontend` | All frontend tests (front-utility → front-ai-export) |

---

## 🏗️ Architecture Overview

```mermaid
---
config:
  layout: elk
---
graph TD
    ALL["./dev.py test all"]

    ALL --> BACKEND["Backend Tests<br/><small>./dev.py test all-backend</small>"]
    ALL --> FRONTEND["Frontend Tests<br/><small>./dev.py test all-frontend</small>"]

    BACKEND --> EXT["External<br/><small>Provider integrations</small>"]
    BACKEND --> DB["Database<br/><small>Schema, migrations,<br/>constraints, persistence</small>"]
    BACKEND --> SVC["Services<br/><small>Business logic</small>"]
    BACKEND --> UTL["Utils<br/><small>Helper functions</small>"]
    BACKEND --> SCH["Schemas<br/><small>Pydantic validation</small>"]
    BACKEND --> API["API<br/><small>FastAPI endpoints</small>"]
    BACKEND --> E2E["E2E<br/><small>API integration</small>"]

    FRONTEND --> FU["Front-Utility<br/><small>Auth, settings, files, select,<br/>image crop, onboarding, layout</small>"]
    FRONTEND --> FB["Front-Broker<br/><small>Broker list, CRUD,<br/>detail page</small>"]
    FRONTEND --> FUSR["Front-User<br/><small>Multi-user isolation,<br/>broker sharing</small>"]
    FRONTEND --> FFX["Front-FX<br/><small>FX list, detail, add-pair,<br/>editor, CSV import, sync</small>"]
    FRONTEND --> FA["Front-Asset<br/><small>Asset list, detail, modal,<br/>data editor, merge</small>"]
    FRONTEND --> FTX["Front-Transaction<br/><small>Modals, table, bulk<br/>operations, WAC, import</small>"]
    FRONTEND --> FP["Front-Portfolio<br/><small>Dashboard, banners,<br/>privacy masking, risk</small>"]
    FRONTEND --> FAI["Front-AI-Export<br/><small>Panel, catalog,<br/>memory, contracts</small>"]
```

---

## 📑 Category Details

### 🔧 Backend Categories

- **[External](external.md)** — Tests the provider plugins, without the backend server. The FX and asset provider tests call the real external APIs, so they need an internet connection; the BRIM import plugins are tested on the local sample files of `backend/app/services/brim_providers/sample_reports/`, with no network.
- **[Database](db.md)** — Tests the database layer directly (schema validation, persistence, migrations). Uses an isolated test SQLite file.
- **[Services](services.md)** — Tests the service layer business logic, often with mocked dependencies.
- **[Utils](utils.md)** — Tests utility modules and helper functions.
- **[Schemas](schemas.md)** — Tests Pydantic model validation, serialization, and edge cases.
- **[API](api.md)** — Integration tests for FastAPI endpoints. Automatically starts a test server if needed.
- **[E2E](e2e.md)** — End-to-end backend tests with real API interaction and database state.

### 🎭 Frontend Categories (Playwright)

Every frontend category also runs Vitest unit files next to its Playwright specs. The categories
without a walkthrough page list their actions with `./dev.py test <category> -h`.

- **[Front-Utility](front-utility.md)** (`./dev.py test front-utility all`) — Tests UI components and app-wide flows: authentication, settings tabs, file upload and management, search selects, image cropping, the onboarding tour and guides, layout, and the scheduler settings.
- **Front-Broker** (`./dev.py test front-broker all`) — Tests the Brokers module: broker list and CRUD, detail page, deletion recovery, creation feedback.
- **[Front-User](front-user.md)** (`./dev.py test front-user all`) — Tests multi-user scenarios: data isolation between users, broker sharing with RBAC.
- **[Front-FX](front-fx.md)** (`./dev.py test front-fx all`) — Tests the FX module: pair list, detail chart, add-pair modal, data editor, CSV import, sync, bulk actions, and FX-specific API calls.
- **Front-Asset** (`./dev.py test front-asset all`) — Tests the Asset module: asset list, detail page, create/edit modal, data editor, merge, classification.
- **Front-Transaction** (`./dev.py test front-transaction all`) — Tests the Transactions module: bulk and form modals, transactions table, split and promote, WAC, import wizard.
- **Front-Portfolio** (`./dev.py test front-portfolio all`) — Tests the Dashboard and the risk views: charts, data-quality banners, page cache, privacy masking, risk analysis.
- **Front-AI-Export** (`./dev.py test front-ai-export all`) — Tests AI Export: panel, catalog, session memory, public contracts.

!!! info "Frontend tests require a running server"

    Before its Playwright specs, a frontend category builds the frontend when its sources changed (or when the build is not of the kind the run needs, instrumented for JS coverage or plain), and the test database is repopulated and the E2E users created, by the runner or by Playwright's `globalSetup`. The specs then run against a backend that also serves the build: the run's shared backend or, with `--no-shared-server`, the one Playwright starts itself. Use `--headed` to watch the browser in action.

---

## 📊 Coverage

### File Architecture

Coverage data is stored in SQLite databases and HTML reports:

```text
LibreFolio/
├── .coveragerc                 # Coverage configuration (parallel=true, sigterm=true)
├── .coverage                   # Working copy — swapped in/out by scripts/test_runner/
├── .coverage_data/
│   ├── backend                 # Accumulated backend-only coverage DB
│   ├── frontend                # Python coverage of the last E2E coverage run
│   └── 00_archive/             # Earlier versions, compressed (scripts/test_runner/_archive.py)
│       ├── backend_20260416_093012.tar.xz
│       ├── backend_clean_20260416_095107.tar.xz
│       └── frontend_20260415_142033.tar.xz
├── htmlcov-backend/            # HTML report: Python, driven by backend tests
├── htmlcov-backend-e2e/        # HTML report: Python, driven by frontend E2E
├── htmlcov/                    # HTML report: Python, combined
└── frontend/coverage-js/       # JS/Svelte coverage (unit, e2e, combined)
```

An archive is named `<label>_<YYYYMMDD_HHMMSS>.tar.xz` (`.tar.bz2`, `.tar.gz` or plain `.tar` when
the Python build lacks `lzma`). The end of a coverage run archives the database it is about to
overwrite (`backend` or `frontend`); `--cov-clean-backend` and `--cov-clean-backend-e2e` archive the
database they remove (`backend_clean`, `frontend_clean`); and before a coverage run, a database that
cannot be read or was recorded in the other measurement mode (statement instead of branch, or the
reverse) is moved into the archive (`backend_mode_change`, `frontend_mode_change`, and
`root_mode_change` for `.coverage`).

| File | Updated by | Contains |
|------|-----------|----------|
| `.coverage` | pytest-cov (working copy) | Temporary — swapped in before pytest, swapped out after |
| `.coverage_data/backend` | `run_command()` finally block | Accumulated backend-only coverage, grows with each backend test run |
| `.coverage_data/frontend` | `_finalize_coverage()` | Server subprocess coverage from Playwright E2E |
| `htmlcov-backend/` | `_finalize_coverage()` | HTML report from `.coverage_data/backend` |
| `htmlcov-backend-e2e/` | `_finalize_coverage()` | HTML report from `.coverage_data/frontend` |
| `htmlcov/` | `_finalize_coverage()` | HTML report from merged backend + frontend |
| `frontend/coverage-js/` | `_finalize_js_coverage()` | JS/Svelte reports — see [Coverage Model](coverage-model.md) |

### Running with Coverage

#### Full Run (clean baseline)

```bash
# Full test suite with coverage: first the language (all = Python + JS), then the suite (all)
./dev.py test --coverage all all

# Clean stale data before a fresh run
./dev.py test --coverage --cov-clean-backend --cov-clean-backend-e2e all
```

`all` is both a coverage language and a suite name, and `--coverage` takes the word after it as its
language whenever that word is one. So name the language before the suite `all` (`--coverage all all`,
`--coverage py all`): `./dev.py test --coverage all` uses `all` as the language, is left without a
suite and stops with *test category required*. Any other category can follow `--coverage` directly
(`./dev.py test --coverage services all`).

#### Incremental Runs (append to existing)

After a full run, you can run individual test files and the coverage **accumulates**
in the existing `.coverage` database thanks to `--cov-append`:

```bash
# Run only specific tests — coverage is added to the existing DB
./dev.py test --coverage services static-uploads
./dev.py test --coverage services fx-core
./dev.py test --coverage utils day-count

# The HTML report (htmlcov-backend/) is regenerated after each run
# The .coverage_data/backend snapshot is updated automatically
```

!!! tip "Incremental coverage workflow"

    1. Run `./dev.py test --coverage all all` once to establish a baseline
    2. Write new tests
    3. Run only the new test file with `--coverage` — it appends to the existing DB
    4. Check the updated report with `./dev.py test coverage show backend`

#### Viewing Reports

```bash
./dev.py test coverage show backend    # open htmlcov-backend/
./dev.py test coverage show frontend   # open htmlcov-backend-e2e/
./dev.py test coverage show combined   # open htmlcov/ (merged)

./dev.py test coverage show js         # open frontend/coverage-js/combined/
./dev.py test coverage show js-unit    # open frontend/coverage-js/unit-combined/
./dev.py test coverage show js-e2e     # open frontend/coverage-js/e2e/
```

### Coverage Isolation

The `.coveragerc` uses `parallel = true` (required for frontend subprocess coverage).
This causes `coverage combine` to pick up **all** `.coverage.*` files and delete them.

To keep backend and frontend coverage properly isolated, the test runner uses a
**swap-in/swap-out** pattern with a dedicated `.coverage_data/` folder:

```text
Before pytest (run_command):
  .coverage_data/backend ──copy──▶ .coverage    (restore accumulated DB)

During pytest:
  pytest-cov runs with --cov-append → appends to .coverage
  parallel=true writes .coverage.HOST.PID, then combines → .coverage
  (.coverage_data/ folder is safe — combine only looks in root)

After pytest (finally block):
  .coverage ──copy──▶ .coverage_data/backend    (save accumulated DB)

After all tests (_finalize_coverage):
  .coverage_data/backend → htmlcov-backend/     (generate HTML report)
  .coverage_data/frontend → htmlcov-backend-e2e/
  merge both → htmlcov/                          (combined report)
```

!!! tip "Why `.coverage_data/` instead of `.coverage.backend`?"

    With `parallel = true`, `coverage combine` picks up **all** files matching
    `.coverage.*` in the current directory. A file named `.coverage.backend` would
    be consumed and deleted. Files in a subdirectory are safe.

### Frontend Coverage Architecture

!!! info "This section is about **Python** coverage driven by the E2E suite"

    For JS/Svelte coverage — the frontend's *own* code — see
    [Coverage Model](coverage-model.md).

Backend coverage during Playwright E2E tests requires a precise signal chain so that
`coverage run` receives SIGTERM (not SIGKILL) and can write `.coverage.<pid>` data.

**4 required elements:**

1. **`gracefulShutdown`** in `playwright.config.ts` — sends SIGTERM instead of SIGKILL
2. **`exec`** in the shell command — shell replaces itself with `dev.py`
3. **`os.execvpe()`** in `dev.py` — replaces itself with `pipenv run coverage run`
4. **`sigterm = true`** in `.coveragerc` — coverage catches SIGTERM and writes data

```mermaid
graph LR
    PW["Playwright<br/><small>gracefulShutdown<br/>sends SIGTERM</small>"]
    SH["/bin/sh<br/><small>exec (level 1)</small>"]
    DP["dev.py<br/><small>os.execvpe (level 2)</small>"]
    PP["pipenv<br/><small>os.execvpe (level 3)</small>"]
    CR["coverage run<br/><small>-m uvicorn</small>"]

    PW -->|SIGTERM| SH
    SH -->|"replaces itself"| DP
    DP -->|"replaces itself"| PP
    PP -->|"replaces itself"| CR

    style CR fill:#4caf50,color:#fff
```

All four steps share the **same PID**. When Playwright sends SIGTERM, it reaches
`coverage run` directly. The `.coveragerc` option `sigterm = true` catches it and
writes `.coverage.<pid>` before the process exits.

!!! danger "Without `gracefulShutdown`"

    By default, Playwright sends **SIGKILL** to terminate the webServer.
    SIGKILL cannot be caught or handled — the process is killed instantly
    and no coverage data is ever written. This is the most common cause of
    missing `htmlcov-backend-e2e/`.

!!! warning "Without `exec` at any level"

    If any level uses `subprocess.run()` instead of exec, SIGTERM only reaches
    the parent process. The child (`coverage run`) becomes an **orphan** and no
    coverage data is written.

!!! danger "The grace window must be wide enough"

    SIGTERM is only half the story: Playwright falls back to **SIGKILL** once the
    `gracefulShutdown.timeout` expires. Flushing the coverage data file takes real
    time, and the default 5 s was not always enough — when it wasn't, the run lost
    **all** backend coverage and reported only a terse
    `No .coverage.* files found!` at the end, which looks like a configuration
    problem rather than a race.

    The timeout is therefore widened to **30 s whenever `COVERAGE_BACKEND` is set**,
    and left at 5 s otherwise (outside coverage there is nothing to flush, so a slow
    shutdown would only waste time).
