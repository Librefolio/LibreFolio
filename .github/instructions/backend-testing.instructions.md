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

**Global flags come BEFORE the category**: `./dev.py test -q --coverage services all`.
Extra positional args after `<category> <action>` are consumed as a pytest `-k` filter.

## ⚠️ Coverage: partial runs report falsely LOW

Coverage accumulates across categories in `.coverage_data/backend`. Measuring only the
*unit* categories reported **75.65 %** on this repo, with `api/` at 31.6 % and
`brim_providers/` at 34.8 %. The complete run reports **90.48 %**, 87.2 % and 84.8 %.

- Always declare **which categories were run** next to any coverage number.
- A comparable figure needs `services` + `schemas` + `utils` + `db` + `api all` +
  `external {brim,fx,asset}-providers` (~50 min).
- `coverage-report` reads `/tmp/cov_report.json`; regenerate it from the live DB first.
- Coverage cannot see `multiprocessing` spawn children (`risk/quant/spawn_worker.py`
  always reads 0 %) — never infer dead code from that alone.

See skill `testing-backend` for the full command sequence and rationale.

## Resume Interrupted Runs

When a test fails mid-suite, fix the issue and resume from where it stopped:

```bash
./dev.py test --resume all-backend       # Skip already-passed, restart from failure
./dev.py test --resume api all           # Same for a single category's "all"

./dev.py test --run-status               # Show current cache (what passed, where stopped)
./dev.py test --fresh-run all-backend    # Clear cache + run from scratch
./dev.py test --fresh-run                # Just clear cache (no run)
```

**How it works**:
- Cache: `scripts/test_runner/.run_cache.json` (gitignored)
- Each suite tracks passed test names; on `--resume` skips them
- When entire suite passes: cache auto-clears (cycle complete)
- `--fresh-run`: explicitly clears all cached state

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

## ⛔ The three rules — normative

Every backend test runs against **one shared database** and **one shared backend**,
concurrently with its neighbours. A test that assumes it is alone is not "simpler":
it is broken, and serialisation was only hiding it.

### 1. Never identify data by position

`[0]`, `[-1]`, "the first page", a fixed index into a list. Another test creates a
row, the order shifts, and the assertion fails somewhere unrelated to its cause.

```python
# ✘ passes only while nothing else writes
resp = await client.get(f"{API_BASE}/assets", headers=h)
asset = resp.json()["items"][0]
assert asset["display_name"] == name

# ✔ write-safe by construction: identified by what this test created
name = f"MyTest {unique_id()}"
created = (await client.post(f"{API_BASE}/assets", json={"display_name": name}, headers=h)).json()
asset = next(a for a in resp.json()["items"] if a["id"] == created["id"])
```

If the endpoint pages, **walk the pages** until the id is found, and fail with
"not found in N pages". Do not assert on page 1 and hope.

### 2. Never assert a count you did not create

```python
# ✘ a neighbour adding one asset breaks this
assert len(resp.json()["items"]) == 3

# ✔ says what it means: my three are there
ids = {a["id"] for a in resp.json()["items"]}
assert {a1, a2, a3} <= ids
```

`len(x) == N` is legitimate only when the count **is** the thing under test — a
paginated `page_size`, a bulk operation's result cardinality — and then it is
asserted on a collection the test owns entirely.

### 3. Never wait on the clock

`time.sleep()` is not a synchronisation primitive. Poll the condition that
actually matters, with a deadline:

```python
# ✘
await asyncio.sleep(2)
resp = await client.get(f"{API_BASE}/jobs/{job_id}", headers=h)
assert resp.json()["status"] == "done"

# ✔
deadline = time.monotonic() + 30
while time.monotonic() < deadline:
    resp = await client.get(f"{API_BASE}/jobs/{job_id}", headers=h)
    if resp.json()["status"] != "pending":
        break
    await asyncio.sleep(0.1)
assert resp.json()["status"] == "done"
```

### 4. Tests do not start servers

The backend is an **environment resource**, started once by the runner. A module
that starts its own uvicorn takes the port from everyone else and makes the
category serial by construction. `_TestingServerManager` attaches to the shared
backend when `LIBREFOLIO_TEST_SHARED_SERVER` is set — do not bypass it.

### 5. Needing an exclusive resource requires a written reason

A unit that cannot share the database stays `WRITE_GLOBAL`, but the catalogue
requires one line saying **what** it mutates that cannot be scoped. "It's easier"
is not a reason; "it rewrites `global_settings`, a single row shared by every
user" is.

Declare it where it is true — on the unit, or as `default_isolation=` on the
category when it holds for the whole category:

```python
add_test(
    "auth", ...,
    exclusive_because="flips global_settings.enable_registration to False; every "
                      "concurrent user creation fails while it is down",
)
```

`exclusive_because` **is** the `WRITE_GLOBAL` declaration, not a comment beside a
flag — a category default cannot silently promote a unit somebody explained must
not be promoted.

### 6. Never reach a third party over the network

A test that calls the real ECB is not testing the ECB — it is testing today's
weather. It fails when the provider is slow, and it makes the whole category
exclusive to protect a timeout. Use the mock providers that already exist
(`MOCKFX`, `MOCKFX_FAIL`, and their asset-source equivalents): they return fixed
values, which lets the assertion be **exact** instead of "some number arrived".

> When a test fails and the cause is not obvious, use the **`test-triage`**
> skill: it gives the ordered hypotheses, starting with *"was it the shape of the
> response?"* — which in this codebase is the most common cause and the easiest to
> misdiagnose as flakiness. **`flaky` is not a verdict.**

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

