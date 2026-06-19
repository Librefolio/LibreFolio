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

# Run a specific test file
./dev.py test api test_auth_api

# List available tests (without running them)
./dev.py test api --list
```

### 🌐 Global Flags

| Flag | Description |
|------|-------------|
| `--verbose` / `-v` | Show full pytest output |
| `--coverage` | Run with code coverage tracking |
| `--cov-clean-backend` | Clean backend coverage data (`htmlcov-backend/` + `.coverage` files) |
| `--cov-clean-frontend` | Clean frontend coverage data (`htmlcov-frontend/` + `.coverage` files) |

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

LibreFolio organizes tests into **11 categories**, grouped by layer:

| Category | Command | What It Tests |
|----------|---------|---------------|
| **External** | `./dev.py test external all` | Provider integrations (FX, assets, BRIM) — no server needed |
| **Database** | `./dev.py test db all` | SQLite schema, migrations, CRUD — no server needed |
| **Services** | `./dev.py test services all` | Business logic in the service layer |
| **Utils** | `./dev.py test utils all` | Helper functions and utility modules |
| **Schemas** | `./dev.py test schemas all` | Pydantic model validation |
| **API** | `./dev.py test api all` | FastAPI endpoints (auto-starts server) |
| **E2E** | `./dev.py test e2e all` | Backend end-to-end with API interaction |
| **Front-Utility** | `./dev.py test front-utility all` | Auth, settings, files, select, image-crop (Playwright) |
| **Front-User** | `./dev.py test front-user all` | Brokers, multi-user, sharing (Playwright) |
| **Front-FX** | `./dev.py test front-fx all` | FX list, detail, add-pair, editor, sync (Playwright) |
| **Front-Asset** | `./dev.py test front-asset all` | Asset list, detail, modal, data editor (Playwright) |

### 🏃 Meta Categories

| Meta Category | Command | What It Runs |
|---------------|---------|--------------|
| **All** | `./dev.py test all` | All backend + frontend tests |
| **All Backend** | `./dev.py test all-backend` | All backend tests (external → e2e) |
| **All Frontend** | `./dev.py test all-frontend` | All frontend tests (front-utility → front-asset) |

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
    BACKEND --> DB["Database<br/><small>Schema, CRUD</small>"]
    BACKEND --> SVC["Services<br/><small>Business logic</small>"]
    BACKEND --> UTL["Utils<br/><small>Helper functions</small>"]
    BACKEND --> SCH["Schemas<br/><small>Pydantic validation</small>"]
    BACKEND --> API["API<br/><small>FastAPI endpoints</small>"]
    BACKEND --> E2E["E2E<br/><small>API integration</small>"]

    FRONTEND --> FU["Front-Utility<br/><small>Auth, settings, files,<br/>select, image-crop</small>"]
    FRONTEND --> FUSR["Front-User<br/><small>Brokers, multi-user,<br/>sharing</small>"]
    FRONTEND --> FFX["Front-FX<br/><small>FX list, detail,<br/>add-pair, editor, sync</small>"]
    FRONTEND --> FA["Front-Asset<br/><small>Asset list, detail,<br/>modal, data editor</small>"]
```

---

## 📑 Category Details

### 🔧 Backend Categories

- **[External](external.md)** — Tests that call real external APIs (FX providers, asset providers, BRIM parsers). Run without the backend server.
- **[Database](db.md)** — Tests the database layer directly (schema validation, persistence, migrations). Uses an isolated test SQLite file.
- **[Services](services.md)** — Tests the service layer business logic, often with mocked dependencies.
- **[Utils](utils.md)** — Tests utility modules and helper functions.
- **[Schemas](schemas.md)** — Tests Pydantic model validation, serialization, and edge cases.
- **[API](api.md)** — Integration tests for FastAPI endpoints. Automatically starts a test server if needed.
- **[E2E](e2e.md)** — End-to-end backend tests with real API interaction and database state.

### 🎭 Frontend Categories (Playwright)

- **[Front-Utility](front-utility.md)** — Tests UI components: authentication flow, settings tabs, file upload, search selects, image cropping.
- **[Front-User](front-user.md)** — Tests user-facing features: broker CRUD, multi-user scenarios, broker sharing with RBAC.
- **[Front-FX](front-fx.md)** — Tests the FX module: pair list, detail chart, add-pair modal, data editor, sync, and FX-specific API calls.
- **[Front-Asset](front-overview.md)** — Tests the Asset module: asset list, detail page, create/edit modal, data editor.

!!! info "Frontend tests require a running server"

    Frontend categories automatically start both the backend server and serve the frontend build. Use `--headed` to watch the browser in action.

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
│   ├── frontend                # Accumulated frontend-only coverage DB
│   └── archive/                # Previous versions (timestamped)
│       ├── backend_20260416_0930
│       ├── backend_20260416_0951
│       └── frontend_20260415_1420
├── htmlcov-backend/            # HTML report: backend tests only
├── htmlcov-frontend/           # HTML report: frontend E2E → backend coverage
└── htmlcov/                    # HTML report: combined (backend + frontend merged)
```

| File | Updated by | Contains |
|------|-----------|----------|
| `.coverage` | pytest-cov (working copy) | Temporary — swapped in before pytest, swapped out after |
| `.coverage_data/backend` | `run_command()` finally block | Accumulated backend-only coverage, grows with each backend test run |
| `.coverage_data/frontend` | `_finalize_coverage()` | Server subprocess coverage from Playwright E2E |
| `htmlcov-backend/` | `_finalize_coverage()` | HTML report from `.coverage_data/backend` |
| `htmlcov-frontend/` | `_finalize_coverage()` | HTML report from `.coverage_data/frontend` |
| `htmlcov/` | `_finalize_coverage()` | HTML report from merged backend + frontend |

### Running with Coverage

#### Full Run (clean baseline)

```bash
# Full test suite with coverage — generates all 3 reports
./dev.py test --coverage all

# Clean stale data before a fresh run
./dev.py test --coverage --cov-clean-backend --cov-clean-frontend all
```

#### Incremental Runs (append to existing)

After a full run, you can run individual test files and the coverage **accumulates**
in the existing `.coverage` database thanks to `--cov-append`:

```bash
# Run only specific tests — coverage is added to the existing DB
./dev.py test --coverage services static-uploads
./dev.py test --coverage services fx-core
./dev.py test --coverage utils day-count

# The HTML report (htmlcov-backend/) is regenerated after each run
# The .coverage.backend snapshot is updated automatically
```

!!! tip "Incremental coverage workflow"

    1. Run `./dev.py test --coverage all` once to establish a baseline
    2. Write new tests
    3. Run only the new test file with `--coverage` — it appends to the existing DB
    4. Check the updated report with `./dev.py test coverage show backend`

#### Viewing Reports

```bash
./dev.py test coverage show backend    # open htmlcov-backend/
./dev.py test coverage show frontend   # open htmlcov-frontend/
./dev.py test coverage show combined   # open htmlcov/ (merged)
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
  .coverage_data/frontend → htmlcov-frontend/
  merge both → htmlcov/                          (combined report)
```

!!! tip "Why `.coverage_data/` instead of `.coverage.backend`?"

    With `parallel = true`, `coverage combine` picks up **all** files matching
    `.coverage.*` in the current directory. A file named `.coverage.backend` would
    be consumed and deleted. Files in a subdirectory are safe.

### Frontend Coverage Architecture

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
    missing `htmlcov-frontend/`.

!!! warning "Without `exec` at any level"

    If any level uses `subprocess.run()` instead of exec, SIGTERM only reaches
    the parent process. The child (`coverage run`) becomes an **orphan** and no
    coverage data is written.
