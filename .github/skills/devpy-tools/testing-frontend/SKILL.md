---
name: testing-frontend
description: "Use this skill when creating, modifying, or running Playwright E2E tests for the frontend, including gallery screenshot generation, test fixtures, and backend coverage tracking during E2E tests."
---

# Frontend Testing Reference (Playwright E2E)

## Test Structure

```text
frontend/
├── e2e/                        # 190+ Playwright E2E tests
│   ├── fixtures/               # Shared helpers
│   │   ├── auth-helpers.ts     # login(), logout(), setLanguage(), navigateTo()
│   │   ├── db-helpers.ts       # resetDatabase(), populateDatabase()
│   │   ├── test-users.ts       # TEST_USER, TEST_ADMIN, TEST_USER_2, ALICE/BOB/CAROL/DAVE/EVE
│   │   └── i18n-data.ts        # Expected translation data for i18n tests
│   ├── auth.spec.ts            # Login, register, logout
│   ├── settings.spec.ts        # User & global settings
│   ├── files.spec.ts           # File management
│   ├── gallery.spec.ts         # Automatic screenshots for docs
│   ├── fx/                     # FX-specific tests
│   ├── assets/                 # Asset-specific tests
│   ├── brokers/                # Broker + sharing + multi-user tests
│   └── transactions/           # Transaction tests (modular per concern)
│       ├── transactions-modals.spec.ts   # CRUD, BulkModal, FormModal, paired
│       ├── transactions-table.spec.ts    # Read-view: pairs, ghost rows, GoTo
│       ├── tx-broker-access.spec.ts      # Broker dropdown, hidden lock, filters
│       ├── tx-paired-edit.spec.ts        # Clone, paired edit payload, adjacency
│       └── tx-tooltips.spec.ts           # Linked pair tooltip HTML rendering
├── playwright.config.ts        # Config (2 projects: desktop + mobile)
└── playwright-report/          # Generated HTML report
```

## How to Run

```bash
# Frontend test categories (via dev.py)
./dev.py test front-utility all         # auth, settings, files, select, image-crop
./dev.py test front-user all            # brokers, multi-user, sharing
./dev.py test front-fx all              # unit (Vitest) + E2E fx
./dev.py test front-asset all           # list, detail, modal, data-editor
./dev.py test front-transaction all     # all transaction E2E tests

# Single sub-category
./dev.py test front-transaction tx-broker-access    # broker access visibility
./dev.py test front-transaction tx-paired-edit      # paired edit/clone
./dev.py test front-transaction tx-tooltips         # tooltip rendering
./dev.py test front-transaction transactions-modals # CRUD flows
./dev.py test front-transaction transactions-table  # read-view table

# With interactive UI
./dev.py test front-transaction tx-broker-access --ui

# With visible browser
./dev.py test front-transaction tx-broker-access --headed

# With backend coverage tracking
./dev.py test --coverage front-transaction all

# Gallery screenshots
./dev.py mkdocs gallery
./dev.py mkdocs gallery --desktop-only
./dev.py mkdocs gallery -f "assets"
./dev.py mkdocs gallery -l              # list available tests
```

## Playwright Config

- **2 projects**: `desktop` (1280×720, Chrome) + `mobile` (iPhone 14 Pro Max viewport, Chromium)
- **Workers**: 1 (sequential — shared DB state)
- **Timeout**: 15s per test (localhost — fast responses expected)
- **Web Server auto-start**: `./dev.py server --test --force` (port 8001)
- **Retry**: 0 local, 2 in CI

## Fixtures

```typescript
import {login, logout, setLanguage, navigateTo} from '../fixtures/auth-helpers';
import {resetDatabase, populateDatabase} from '../fixtures/db-helpers';
import {TEST_USER, TEST_ADMIN} from '../fixtures/test-users';

await login(page);                    // Login with default TEST_USER
await login(page, TEST_ADMIN);        // Login as admin
await setLanguage(page, 'it');        // Change language
await resetDatabase();                // Full reset (create-clean + populate)
```

## How to Create a Test

### Step 1: Choose the right spec file

Tests are organized **per concern**, not per page. Each spec file covers one functional area:

| File pattern | Scope |
|-------------|-------|
| `transactions-modals.spec.ts` | Core CRUD flow (create, edit, delete, clone) |
| `transactions-table.spec.ts` | Read-view rendering and interactions |
| `tx-{concern}.spec.ts` | Specific bug-fix or feature area |

For a **new concern** (e.g. a new group of bugs or a feature), create a new file: `tx-{concern}.spec.ts`.

### Step 2: Write the test

```typescript
import {test, expect} from '@playwright/test';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

test.setTimeout(15_000);

test.describe('Feature Name', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await navigateTo(page, '/transactions');
        await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 8_000});
    });

    test('should do something', async ({page}) => {
        await page.getByTestId('some-button').click();
        await expect(page.getByTestId('result-element')).toContainText('Expected');
    });
});
```

### Step 3: Register in the test runner

Edit `scripts/test_runner/_frontend_transaction.py`:

1. Add a **runner function**:
```python
def front_tx_my_concern(verbose=False, ui=False, headed=False, debug=False, test_names=None, coverage=False):
    """Run TX My Concern E2E tests."""
    print_section("Frontend TX My Concern Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("transactions/tx-my-concern.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)
```

2. Add it to `front_transaction_all()`:
```python
("TX My Concern", lambda: front_tx_my_concern(verbose=verbose, ui=ui, ...)),
```

3. Register in `populate_registry()`:
```python
add_test(cat, "tx-my-concern", front_tx_my_concern,
    name="TX My Concern Tests",
    desc="Description of what it tests",
    tests="transactions/tx-my-concern.spec.ts")
```

After this, it's available via: `./dev.py test front-transaction tx-my-concern`

## Mock Data Contract

Tests depend on `populate_mock_data.py` for deterministic data. The test runner calls `db populate --force` before every suite.

**Key principle: never use `test.skip()` for missing mock data.** If a test needs specific data (e.g. paired transactions, INTEREST type, broker with VIEWER role), that data **must** exist in `populate_mock_data.py`. If a test fails because expected data is missing, fix the seeding — don't skip the test.

When mock data is missing, the test should **throw** with a clear message pointing to `populate_mock_data.py`:
```typescript
throw new Error('Row "Asym-d" not found. Check populate_mock_data.py seeding.');
```

Reserve `test.skip()` only for **infrastructure** conditions (e.g. mobile-only test on desktop project, or a test that requires an external service).

## Backend Coverage during E2E

The SIGTERM chain: Playwright `gracefulShutdown` → `exec` in shell → `os.execvpe()` in dev.py → `coverage run -m uvicorn`. All exec calls replace the process so SIGTERM reaches `coverage run` which writes `.coverage.*`.

Key files:
- `playwright.config.ts`: `gracefulShutdown: {signal: 'SIGTERM', timeout: 5000}`
- `dev.py` (cmd_server): `os.execvpe()` in coverage mode
- `.coveragerc`: `sigterm = true`, `parallel = true`

## Conventions

- **`data-testid` always**: never select by CSS class or text (fragile with i18n)
- **Explicit timeouts**: use `{timeout: N}` on expect/waitFor — keep them tight (localhost is fast)
- **Never skip for missing data**: if mock data is needed, ensure it exists in `populate_mock_data.py`
- **Mobile awareness**: handle hamburger menu with `openMobileMenu()`
- **No hardcoded login**: always use `login()` from `auth-helpers.ts`
- **Request interception**: use `page.waitForRequest()` to verify commit payloads

## Test Runner Architecture (`scripts/test_runner/`)

All tests are orchestrated by a modular Python test runner, invoked via `./dev.py test`.

```text
scripts/test_runner/
├── _registry.py              # TEST_REGISTRY — single source of truth
├── _cli.py                   # Argument parsing + dispatch
├── _common.py                # Shared utilities (run_command, add_test, _run_test_suite)
├── _suites.py                # Aggregate suites (all, all-backend, all-frontend)
├── _frontend_common.py       # _run_playwright, _ensure_db_populated, _ensure_test_users
├── _frontend_transaction.py  # Transaction E2E: 5 spec files, 1 "all" suite
├── _frontend_broker.py       # Broker E2E runners
├── _frontend_fx.py           # FX E2E runners
├── _frontend_asset.py        # Asset E2E runners
├── _frontend_utility.py      # Auth/settings/files E2E runners
└── _frontend_user.py         # User-related E2E runners
```

### How it works

1. Each `_frontend_*.py` exports `populate_registry(registry)` which adds entries to `TEST_REGISTRY`
2. `_registry.py` assembles the full registry by calling all pop functions
3. `_cli.py` auto-generates argparse subcommands from `TEST_REGISTRY`
4. `./dev.py test <category> <action>` dispatches to the registered function

### Adding a new frontend test spec

1. Create `frontend/e2e/{domain}/tx-{concern}.spec.ts` (or `{domain}.spec.ts`)
2. In the appropriate `_frontend_{domain}.py`:
   - Add a runner function that calls `_run_playwright("path/to/spec.ts", ...)`
   - Add to the `{domain}_all()` suite
   - Register with `add_test(cat, "action-name", runner_func, ...)`
3. The new action becomes available as `./dev.py test front-{domain} action-name`

### Key functions

| Function | Module | Purpose |
|----------|--------|---------|
| `_run_playwright(spec, ...)` | `_frontend_common.py` | Runs Playwright with ui/headed/debug/coverage flags |
| `_ensure_db_populated()` | `_frontend_common.py` | Calls `db populate --force` before tests |
| `_ensure_test_users()` | `_frontend_common.py` | Creates 8 E2E users if missing |
| `_ensure_frontend_build()` | `_frontend_common.py` | Auto-builds frontend if stale |
| `add_test(cat, action, func, ...)` | `_common.py` | Registers a test entry in a category dict |
| `make_category(help, desc)` | `_common.py` | Creates the `_meta` entry for a new category |
| `_run_test_suite(tests, ...)` | `_common.py` | Runs tests sequentially with summary report |

