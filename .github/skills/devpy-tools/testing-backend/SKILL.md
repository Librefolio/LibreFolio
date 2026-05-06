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
2. **Test port**: `TEST_PORT` (default 8001)
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
- **Formatted output**: use `print_section()`, `print_success()`, `print_error()` from `test_utils.py`
- **Timeout**: `TIMEOUT = 30` seconds for API calls
- **Status codes**: check for both 200 and 201 on creation endpoints (`assert resp.status_code in (200, 201)`)

## Test Runner Architecture (`scripts/test_runner/`)

All tests are orchestrated by a modular Python test runner, invoked via `./dev.py test`.

```text
scripts/test_runner/
├── _registry.py          # TEST_REGISTRY — single source of truth for all tests
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

### Adding a new backend test

Backend API tests are **auto-discovered** by pytest — no manual registration needed:

1. Add a `test_*()` function to an existing `test_*.py` file in `backend/test_scripts/test_api/`
2. It's automatically picked up by `./dev.py test api all`
3. Run individually: `pipenv run pytest backend/test_scripts/test_api/test_file.py::test_func -v`

For a new **category** (not just a new test), create `_backend_{name}.py` with `populate_registry()` and import it in `_registry.py`.

### Key functions

| Function | Module | Purpose |
|----------|--------|---------|
| `_build_pytest_cmd(path, test_names)` | `_common.py` | Builds pytest command with optional `-k` filter |
| `run_command(cmd, description, verbose)` | `_common.py` | Runs subprocess with coverage tracking integration |
| `add_test(cat, action, func, ...)` | `_common.py` | Registers a named test in a category dict |
| `make_category(help, desc)` | `_common.py` | Creates `_meta` entry for a new category |
| `_run_test_suite(tests, ...)` | `_common.py` | Runs tests sequentially with pass/fail summary |

