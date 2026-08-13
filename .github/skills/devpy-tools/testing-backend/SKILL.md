---
name: testing-backend
description: "Use this skill when creating, modifying, or running backend Python tests with pytest, including API tests, service tests, provider tests, coverage analysis, and test database population."
---

# Backend Testing Reference

## Test Structure

```text
backend/test_scripts/
├── test_api/               # 280+ tests — REST endpoints via httpx
│   ├── test_transactions_api.py   # TX CRUD, linked pairs, partner_broker_id
│   ├── test_broker_access_api.py  # Broker access/sharing, role hierarchy
│   ├── test_brokers_api.py        # Broker CRUD
│   └── ...
├── test_db/                # Database layer
├── test_services/          # Business logic
├── test_e2e/               # End-to-end backend flows
├── test_external/          # Provider + network tests
├── test_schemas/           # Pydantic validation
├── test_utilities/         # Utility functions
├── test_server_helper.py   # Auto-start server for API tests
└── test_utils.py           # Output formatting, helpers
```

## How to Run

```bash
# All backend tests (800+)
./dev.py test all-backend

# Single category
./dev.py test api all
./dev.py test db all
./dev.py test services all
./dev.py test external all    # needs network

# With coverage
./dev.py test --coverage api all

# With verbose output
./dev.py test --verbose api all

# Filter external providers (useful when a service is down)
./dev.py test --exclude-providers yfinance external asset-providers 
./dev.py test --exclude-providers yfinance all 

# Single file (bypass dev.py)
pipenv run pytest backend/test_scripts/test_api/test_transactions_api.py -v

# Single test
pipenv run pytest backend/test_scripts/test_api/test_transactions_api.py::test_get_transactions_partner_broker_id -v
```

## API Test Architecture

API tests use `_TestingServerManager` from `test_server_helper.py`:

1. **Server as thread**: uvicorn runs in a thread within pytest process → enables `pytest-cov` coverage tracking
2. **Test port**: `TEST_PORT` (default 6041)
3. **Isolated test DB**: `backend/data/test/sqlite/app.db`
4. **HTTP Client**: `httpx.AsyncClient`

### Pattern for an API test

```python
import httpx
import pytest
from backend.app.config import get_settings
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success, unique_id

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30

async def create_user_and_login(client: httpx.AsyncClient) -> None:
    import uuid, time
    username = f"test_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4]}"
    await client.post(f"{API_BASE}/auth/register",
        json={"username": username, "email": f"{username}@test.com", "password": "TestPass123!"},
        timeout=TIMEOUT)
    await client.post(f"{API_BASE}/auth/login",
        json={"username": username, "password": "TestPass123!"}, timeout=TIMEOUT)

@pytest.mark.asyncio
class TestFeatureX:
    @pytest.fixture(autouse=True)
    def server(self):
        mgr = _TestingServerManager()
        mgr.ensure_started()
        yield

    async def test_create_something(self):
        print_section("Create Something")
        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)
            resp = await client.post(f"{API_BASE}/something", json={...}, timeout=TIMEOUT)
            assert resp.status_code == 201
```

## How to Add a New Backend Test

### Step 1: Choose the right file

Tests go in the appropriate `test_api/` file based on the endpoint being tested:

| Endpoint | File |
|----------|------|
| `/transactions/*` | `test_transactions_api.py` |
| `/brokers/*` | `test_brokers_api.py` |
| `/brokers/{id}/access` | `test_broker_access_api.py` |
| `/assets/*` | `test_assets_*.py` |
| `/fx/*` | `test_fx_api.py` |

### Step 2: Write the test function

```python
@pytest.mark.asyncio
async def test_my_new_feature(test_server):
    """TX-A-XXX: Description of what this tests."""
    print_section("Test TX-A-XXX: Description")

    async with httpx.AsyncClient() as client:
        await create_test_user(client)

        # Setup: create broker, asset, etc.
        # Action: call the endpoint
        # Assert: verify the response

        print_success("✓ Feature works as expected")
```

### Step 3: Registration

Backend tests are auto-discovered by pytest from the `test_api/` directory. No manual registration needed — just add the function to an existing `test_*.py` file and it will be picked up by `./dev.py test api all`.

The test runner modules in `scripts/test_runner/_backend_api.py` register entire directories, not individual files.

## Mock Data

`populate_mock_data.py` creates deterministic data:
- Users: `e2e_test_user` and `e2e_test_admin`
- Brokers: 6+ brokers with shared access (OWNER/EDITOR/VIEWER roles)
- Assets: AAPL (yfinance), iShares MSCI World (JustETF), BTP (CSS Scraper), Scheduled Investment
- FX Pairs: EUR/USD, GBP/EUR, USD/CHF with mock rates
- Transactions: 40+ transactions including 4 asymmetric access pairs (Asym-a through Asym-d)
- Hidden Admin Broker: admin-only broker for testing inaccessible partner scenarios

```bash
./dev.py db create-clean --test
./dev.py test db populate --force
./dev.py test db populate --force --clean --with-static --with-reports  # for gallery
```

## Coverage

```bash
./dev.py test --coverage api all
./dev.py test coverage show backend
./dev.py test coverage show combined
./dev.py test coverage-report --priority high  # uncovered functions analysis
```

### `--coverage` takes an optional language

`--coverage [py|js|all]`, defaulting to `all` when omitted. Backend suites can only
ever produce Python coverage, so on them `all` and `py` are equivalent and
`--coverage js api all` is rejected with an explicit error rather than producing an
empty report.

Every form below stays valid — the suite name is never mistaken for a language:

```bash
./dev.py test --coverage api all       # language omitted → all → Python here
./dev.py test --coverage py api all    # explicit
```

The `frontend/coverage-js/` reports come from Playwright and vitest runs; see the
`testing-frontend` skill.

### ⚠️ A partial coverage measurement is worthless — and it lies LOW

Coverage accumulates in `.coverage_data/backend` via `--cov-append`. Running only the
*unit* categories reports code as uncovered when it is in fact covered by API or external
tests. Measured on this repo:

| Scope | Reported total | "Actionable" funcs |
|---|---:|---:|
| unit only (`services`+`schemas`+`utils`+`db`) | 75.65 % | 445 (6 406 stmt) |
| **complete** | **90.48 %** | **42 (155 stmt)** |

`api/` read 31.6 % vs the real 87.2 %; `brim_providers/` read 34.8 % vs the real 84.8 %.
Acting on the partial number would have sent weeks of work to the wrong place.

**Full sequence for a comparable figure** (~50 min):

```bash
./dev.py test -q --coverage services all
./dev.py test -q --coverage schemas all
./dev.py test -q --coverage utils all
./dev.py test -q --coverage db all
./dev.py test -q --coverage api all            # ~20 min, starts a server per group
./dev.py test -q --coverage external brim-providers
./dev.py test -q --coverage external fx-providers      # needs network
./dev.py test -q --coverage external asset-providers   # needs network
```

Rules:

- **Always state which categories were run** alongside any coverage number. A figure
  without that declaration is not comparable to anything.
- Do **not** wrap `api all` in a short `timeout` — it silently truncates the last groups
  and their code then reads as 0 %.
- `coverage-report` reads **`/tmp/cov_report.json`**, not the live DB. Regenerate first:
  `COVERAGE_FILE=.coverage_data/backend pipenv run coverage json -o /tmp/cov_report.json`
- The same command analyses the **frontend** with `--lang js`, reading monocart's istanbul
  JSON from `frontend/coverage-js/` (no regeneration step needed — the test run writes it).
- **Coverage is blind to `multiprocessing` spawn children.** `services/risk/quant/spawn_worker.py`
  (`_worker_main`, `_resolve_handler`, `_peak_rss_bytes`) always reads 0 % while being
  live. Never treat those as dead code — cross-check with `./dev.py lint --dead-code`.

### Coverage as a dead-code cross-check

A symbol at 0 % **and** flagged by vulture is dead with near-certainty: static analysis
can miss dynamic dispatch, but coverage cannot miss code that actually ran. Use the two
together before proposing any removal. See
`LibreFolio_developer_journal/Release_2/Phase_0/05_cleanAudit/12_test_coverage.md`.

## Provider Filtering (--providers / --exclude-providers)

```bash
./dev.py test external -h  # shows available provider codes
./dev.py test external asset-providers --exclude-providers yfinance
./dev.py test all --providers justetf ECB
```

## Conventions

- **Naming**: `test_*.py` for files, `test_*` for functions, `Test*` for classes
- **Isolation**: each test creates its own temporary user (`unique_id`)
- **No side effects**: tests must not depend on execution order
- **Whoever commits, cleans up**: see below — this is now enforced by consolidation, not by luck
- **Formatted output**: use `print_section()`, `print_success()`, `print_error()` from `test_utils.py`
- **Timeout**: `TIMEOUT = 30` seconds for API calls
- **Status codes**: check for both 200 and 201 on creation endpoints (`assert resp.status_code in (200, 201)`)

### ⚠️ Whoever commits, cleans up

Most `session` fixtures flush and roll back, so most tests are compliant for free. **The rule only
bites fixtures that deliberately call `commit()`** — and those must undo their writes after `yield`:

```python
@pytest_asyncio.fixture(scope="module")
async def fx_asset_ids():
    ...                          # writes and commits
    yield asset_id
    async with ... as session:   # and now puts it back
        await session.execute(delete(FxRate).where(...))
        await session.execute(delete(Asset).where(Asset.id == asset_id))
        await session.commit()
```

Why it matters now: the runner used to spend one process per action, so leftovers were invisible.
Under `--workers N` units share invocations, and committed rows become the **next** unit's input.
A committed `('2025-02-01','EUR','USD')` FX row made a test fail *in another file* with
`UNIQUE constraint failed` — the expensive kind of bug, because the failure names the victim rather
than the culprit.

## Test Runner Architecture (`scripts/test_runner/`)

All tests are orchestrated by a modular Python test runner, invoked via `./dev.py test`.

```text
scripts/test_runner/
├── _registry.py          # TEST_REGISTRY — single source of truth for all tests
├── _inventory.py         # Derives what exists: units, isolation classes, reachability
├── _scheduler.py         # inventory + --workers N → execution plan (LPT balanced)
├── _executor.py          # Runs a plan; one resource lot per worker; combines coverage
├── _cli.py               # Argument parsing + dispatch (argparse + argcomplete)
├── _common.py            # Shared: run_command, _build_pytest_cmd, _run_test_suite
├── _suites.py            # Aggregate suites: all, all-backend, all-frontend
├── _coverage.py          # Coverage DB management, combine, finalize
├── _backend_api.py       # Registers "api" + "e2e" categories (pytest runners)
├── _backend_db.py        # "db" category: create-clean, populate
├── _backend_services.py  # "services" category
├── _backend_external.py  # "external" category with --providers/--exclude-providers
├── _backend_schemas.py   # "schemas" category
├── _backend_utils.py     # "utils" category
└── _frontend_*.py        # Frontend E2E categories (one per domain)
```

### How it works

1. Each `_backend_*.py` exports `populate_registry(registry)` → adds entries to `TEST_REGISTRY`
2. `_registry.py` assembles the full registry by calling all pop functions in order
3. `_cli.py` auto-generates argparse subcommands from `TEST_REGISTRY` entries
4. `./dev.py test <category> <action>` dispatches to the registered function via `run_test_from_registry()`

### Running in parallel

`--workers` goes **before** the category, because it belongs to `test` and not to the action:

```bash
./dev.py test --workers 4 services all
./dev.py test --workers auto all-backend      # auto = cpu_count/2
```

`--workers N` never changes *which* tests run — verify that with the count, not with the colour.
See `runner_architecture.md` for the isolation classes and the scheduler.

What runs in parallel is what the catalogue **declares** safe: PURE always, plus every unit given a
`isolation=` (or a category `default_isolation=`). `api`, `services`, `utils` and `schemas` are all
declared `write-scoped` — each unit creates its own user and addresses its own rows by id — with two
exceptions that carry a written `exclusive_because`.

!!! warning "Do not promote a category by reading it — promote it by running it"
    `--assume-scoped` ignores the catalogue and runs everything concurrently. That is how you find
    out what the catalogue was wrong about, and it belongs to that one experiment, not to daily use.
    Read the reds with the `test-triage` skill *before* writing any declaration: on `api` the
    thirteen reds all pointed at the two files that were failing, and the cause was a third one.

Measured on the whole backend: 4654 tests both ways, 0 failures both ways, coverage identical to the
statement (37336 / 3224 / 91.36 %), 38 min 52 s → 31 min 03 s. The parallel pass itself is fast —
51 units and 1494 tests in 32.2 s, workers landing within 0.1 s of each other — so the ceiling is set
by the serial WRITE-GLOBAL remainder, not by the balancing.

Compare coverage **per file**, not on the total: the two live-network provider modules
(`asset_source.py`, `borsa_italiana.py`) vary by a handful of statements between runs depending on
what the remote site returns, so the total carries ~0.01 % of noise that would otherwise be
indistinguishable from lost data. Every other module is reproducible exactly.

That tolerance is a *handful* of statements, and knowing its size is what makes a larger gap
readable. A full `--coverage all --workers 4 all` run reported 91.38 %, then 91.64 % after a frontend
crash was fixed — 98 statements, twenty times the noise floor, and in the direction that looks
harmless. Three frontend specs had been dying mid-run and taking their backend E2E coverage with
them. **Coverage going quietly down is a symptom, not a fluctuation.**

`--no-fail-fast` runs everything and reports every red instead of stopping at the first. It covers
the parallel pass, the consolidation pass and the serial suite, so one flag answers "how wide is the
damage".

!!! info "Port 6041 and `db create` — fixed, and worth knowing why"
    `db create` used to unlink the database *before* `db:upgrade` ran, and `db:upgrade` refuses to
    migrate while a server holds port 6041 — so a run with the shared backend up destroyed the
    database and then failed to rebuild it, producing 116 `no such table: users` errors twenty lines
    below the one message that named the cause.

    Now the precondition is checked **before** anything is destroyed, `db create` pauses the shared
    backend for the duration, and a failed setup is **fatal to its category** instead of a warning
    followed by a hundred misleading errors.

### Adding a new backend test

Backend API tests are **auto-discovered** by pytest — no manual registration needed:

1. Add a `test_*()` function to an existing `test_*.py` file in `backend/test_scripts/test_api/`
2. It's automatically picked up by `./dev.py test api all`
3. Run individually: `pipenv run pytest backend/test_scripts/test_api/test_file.py::test_func -v`

For a new **category** (not just a new test), create `_backend_{name}.py` with `populate_registry()` and import it in `_registry.py`.

### Key functions

| Function | Module | Purpose |
|----------|--------|---------|
| `build_inventory()` | `_inventory.py` | Every unit with its category and isolation class |
| `plan(units, workers)` | `_scheduler.py` | Splits parallel vs serial, balances by measured duration |
| `run_groups(...)` | `_executor.py` | Executes a plan, one `COVERAGE_FILE` per worker |
| `_build_pytest_cmd(path, test_names)` | `_common.py` | Builds pytest command with optional `-k` filter |
| `run_command(cmd, description, verbose)` | `_common.py` | Runs subprocess with coverage tracking integration |
| `add_test(cat, action, func, ...)` | `_common.py` | Registers a named test in a category dict |
| `make_category(help, desc)` | `_common.py` | Creates `_meta` entry for a new category |
| `_run_test_suite(tests, ...)` | `_common.py` | Runs tests sequentially with pass/fail summary |

