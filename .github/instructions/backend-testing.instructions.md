---
applyTo: "backend/test_scripts/**"
---

# Backend Testing Reference

## Structure

```text
backend/test_scripts/
├── test_api/               # 280+ tests — REST endpoints via httpx
│   ├── test_transactions_api.py   # TX CRUD, linked pairs, partner_broker_id
│   ├── test_broker_access_api.py  # Broker access/sharing, role hierarchy
│   ├── test_brokers_api.py        # Broker CRUD
│   ├── test_fx_api.py             # FX pairs
│   ├── test_assets_events.py      # Asset events
│   └── ...
├── test_db/                # Database layer + populate_mock_data.py
├── test_services/          # Business logic
├── test_e2e/               # End-to-end backend flows
├── test_external/          # Provider + network tests
├── test_schemas/           # Pydantic validation
├── test_utilities/         # Utility functions
├── test_server_helper.py   # _TestingServerManager (server-in-thread)
└── test_utils.py           # print_section(), print_success(), unique_id()
```

## Run Commands

```bash
./dev.py test api all              # REST endpoint tests
./dev.py test db all               # Database tests
./dev.py test services all         # Service layer
./dev.py test external all         # Provider tests (needs network)
./dev.py test e2e all              # Backend end-to-end
./dev.py test all-backend          # All backend categories
./dev.py test --coverage api all   # With coverage tracking
```

See skill `testing-backend` for full details on patterns, fixtures, coverage, and provider filtering.

## API Test Pattern

```python
import httpx, pytest
from backend.app.config import get_settings
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success, unique_id

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30

@pytest.mark.asyncio
class TestFeatureX:
    @pytest.fixture(autouse=True)
    def server(self):
        _TestingServerManager().ensure_started()
        yield

    async def test_something(self):
        async with httpx.AsyncClient() as client:
            # create_user_and_login(client) → then test
            ...
```

## Conventions

- **Naming**: `test_*.py` files, `test_*` functions, `Test*` classes
- **Isolation**: each test creates its own temporary user (`unique_id`)
- **No side effects**: tests must not depend on execution order
- **Formatted output**: use `print_section()`, `print_success()` from `test_utils.py`
- **Timeout**: `TIMEOUT = 30` for API calls

## Key Tests by Feature Area

| Feature | Test File | Key Tests |
|---------|-----------|-----------|
| Transaction CRUD | `test_transactions_api.py` | `test_post_transactions_*`, `test_patch_*`, `test_delete_*` |
| Linked pairs | `test_transactions_api.py` | `test_delete_linked_without_pair`, `test_get_transactions_partner_broker_id` |
| Broker access | `test_broker_access_api.py` | Role hierarchy, multi-user isolation |
| Transaction types | `test_transactions_api.py` | `test_get_transaction_types` |

## Test Runner Architecture (`scripts/test_runner/`)

All tests are orchestrated by a modular Python test runner, invoked via `./dev.py test`.

```text
scripts/test_runner/
├── _registry.py          # TEST_REGISTRY — single source of truth for all tests
├── _cli.py               # Argument parsing, dispatch, main entry point
├── _common.py            # Shared: run_command, _build_pytest_cmd, _run_test_suite
├── _suites.py            # run_all_tests, run_all_backend/frontend_tests
├── _coverage.py          # Coverage finalization and reporting
├── _backend_api.py       # Backend API test runners (pytest) — registers "api" + "e2e"
├── _backend_db.py        # DB create-clean, populate
├── _backend_services.py  # Service layer tests
├── _backend_external.py  # Provider/network tests with --providers filter
├── _backend_schemas.py   # Pydantic schema tests
├── _backend_utils.py     # Utility function tests
└── _frontend_*.py        # Frontend E2E runners (one per domain)
```

### How it works

1. Each `_backend_*.py` module exports a `populate_registry(registry)` function
2. `_registry.py` calls all `populate_registry()` functions to build `TEST_REGISTRY`
3. `_cli.py` generates argparse subcommands from `TEST_REGISTRY` dynamically
4. `./dev.py test <category> <action>` dispatches to the registered function

### Adding a new backend test

Backend tests are **auto-discovered** by pytest from the `test_api/` directory. No manual registration needed:

1. Add a `test_*` function to an existing `test_*.py` file (or create a new file)
2. It will be picked up automatically by `./dev.py test api all`
3. Run individually: `pipenv run pytest backend/test_scripts/test_api/test_file.py::test_function -v`

The test runner modules (`_backend_api.py`) register **directories**, not individual files.

### Key functions

| Function | Module | Purpose |
|----------|--------|---------|
| `_build_pytest_cmd(path, test_names)` | `_common.py` | Builds pytest command with optional -k filter |
| `run_command(cmd, description, verbose)` | `_common.py` | Runs subprocess with coverage integration |
| `add_test(cat, action, func, ...)` | `_common.py` | Registers a test in the category dict |
| `_run_test_suite(tests, ...)` | `_common.py` | Runs a list of tests with summary |

