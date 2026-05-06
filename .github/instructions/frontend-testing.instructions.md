---
applyTo: "frontend/e2e/**"
---

# Frontend E2E Testing (Playwright)

## Structure

```text
frontend/e2e/
├── fixtures/               # Shared helpers
│   ├── auth-helpers.ts     # login(), logout(), setLanguage(), navigateTo()
│   ├── db-helpers.ts       # resetDatabase(), populateDatabase()
│   ├── test-users.ts       # TEST_USER, TEST_ADMIN, TEST_USER_2, ALICE/BOB/CAROL/DAVE/EVE
│   └── i18n-data.ts        # Expected translation data
├── auth.spec.ts
├── settings.spec.ts
├── files.spec.ts
├── gallery.spec.ts         # Auto screenshots for docs
├── fx/                     # FX-specific tests
├── assets/                 # Asset-specific tests
├── brokers/                # Broker + sharing + multi-user tests
│   ├── brokers.spec.ts
│   ├── brokers-detail.spec.ts
│   ├── broker-sharing.spec.ts
│   └── multi-user.spec.ts
└── transactions/           # Transaction tests (modular per concern)
    ├── transactions-modals.spec.ts   # CRUD, BulkModal, FormModal, paired, sign-flip
    ├── transactions-table.spec.ts    # Read-view: pairs, ghost rows, GoTo, actions
    ├── tx-broker-access.spec.ts      # Broker dropdown, hidden broker lock, edit visibility, enum filters
    ├── tx-paired-edit.spec.ts        # Clone INTEREST, paired edit payload, flat mode adjacency
    └── tx-tooltips.spec.ts           # Linked pair tooltips: favicon, bold name, SVG role icon
```

## Run Commands

```bash
# By domain
./dev.py test front-utility all       # auth, settings, files
./dev.py test front-broker all        # brokers, sharing, multi-user
./dev.py test front-fx all            # FX tests
./dev.py test front-asset all         # Asset tests
./dev.py test front-transaction all   # All transaction tests

# Individual transaction spec files
./dev.py test front-transaction transactions-modals   # CRUD flow
./dev.py test front-transaction transactions-table    # Read-view table
./dev.py test front-transaction tx-broker-access      # Broker access visibility
./dev.py test front-transaction tx-paired-edit        # Paired edit/clone
./dev.py test front-transaction tx-tooltips           # Tooltip rendering

# All frontend at once
./dev.py test all-frontend

# Options: --ui (Playwright UI), --headed (visible browser), --debug (debug mode)
./dev.py test front-transaction tx-broker-access --headed
```

See skill `testing-frontend` for full details on patterns, fixtures, gallery, and coverage pipeline.

## Test Organization Convention

Tests are organized **per concern**, not monolithically per page. Each spec file covers a specific functional area:

| File | Scope | Bugs Covered |
|------|-------|-------------|
| `transactions-modals.spec.ts` | CRUD, BulkModal, FormModal, paired, sign-flip | Core flow |
| `transactions-table.spec.ts` | Read-view: pair adjacency, links, actions | Core display |
| `tx-broker-access.spec.ts` | Broker dropdown, hidden lock, edit btn, filters | Bug 1, 3, 10, 13 |
| `tx-paired-edit.spec.ts` | Clone INTEREST, paired edit payload, flat mode | Bug 2, 6, 7, 14 |
| `tx-tooltips.spec.ts` | Linked pair tooltip HTML: favicon, name, role SVG | Bug 8 |

**New test files** should follow this pattern: `tx-{concern}.spec.ts`.

## Conventions

- **Always use `data-testid`** — never CSS classes or text (fragile with i18n)
- **Explicit timeouts**: `{timeout: N}` on expect/waitFor — keep tight (localhost is fast, 15s per test)
- **Never skip for missing mock data**: if data is needed, it must exist in `populate_mock_data.py`. Use `throw new Error(...)` pointing to the seeding script instead.
- **Reserve `test.skip()` only for infrastructure conditions** (e.g. mobile-only test on desktop project)
- **Mobile awareness**: handle hamburger menu with `openMobileMenu()`
- **Login via helper**: always use `login()` from `auth-helpers.ts`
- **Mock data**: tests rely on `populate_mock_data.py` — all asymmetric access pairs use tag `access-test`
- **Request interception**: use `page.waitForRequest()` to verify commit payloads (Bug 14 pattern)

## How to Add New Transaction Tests

1. **Create** `frontend/e2e/transactions/tx-{concern}.spec.ts`
2. **Register** in `scripts/test_runner/_frontend_transaction.py`:
   - Add runner function (`front_tx_{concern}`)
   - Add to `front_transaction_all()` tests list
   - Add to `populate_registry()` with `add_test()`
3. **Run**: `./dev.py test front-transaction tx-{concern}`

## Playwright Config

- 2 projects: `desktop` (1280×720) + `mobile` (iPhone 14 Pro Max viewport)
- Both use Chromium (WebKit has stability issues on Linux)
- Workers: 1 (sequential — shared DB state)
- Web Server auto-start: `./dev.py server --test --force`

## Test Runner Architecture (`scripts/test_runner/`)

All tests are orchestrated by a modular Python test runner, invoked via `./dev.py test`.

```text
scripts/test_runner/
├── _registry.py              # TEST_REGISTRY — single source of truth for all tests
├── _cli.py                   # Argument parsing, dispatch, main entry point
├── _common.py                # Shared: run_command, _run_test_suite, make_category, add_test
├── _suites.py                # run_all_tests, run_all_backend/frontend_tests
├── _coverage.py              # Coverage finalization and reporting
├── _frontend_common.py       # _ensure_frontend_build, _ensure_db_populated, _run_playwright
├── _frontend_transaction.py  # Transaction E2E runners + registry population
├── _frontend_broker.py       # Broker E2E runners
├── _frontend_fx.py           # FX E2E runners
├── _frontend_asset.py        # Asset E2E runners
├── _frontend_utility.py      # Auth, settings, files E2E runners
├── _frontend_user.py         # User-related E2E runners
├── _backend_api.py           # Backend API test runners (pytest)
├── _backend_db.py            # DB populate, create-clean
└── ...                       # Other backend categories
```

### How it works

1. Each `_frontend_*.py` / `_backend_*.py` module exports a `populate_registry(registry)` function
2. `_registry.py` calls all `populate_registry()` functions to build `TEST_REGISTRY`
3. `_cli.py` generates argparse subcommands from `TEST_REGISTRY` dynamically
4. `./dev.py test <category> <action>` dispatches to the registered function

### Adding a new frontend test

1. Create `frontend/e2e/transactions/tx-{concern}.spec.ts`
2. In `scripts/test_runner/_frontend_transaction.py`:
   - Add runner function: `def front_tx_{concern}(...)`
   - Add to `front_transaction_all()` tests list
   - Add to `populate_registry()` with `add_test(cat, "tx-{concern}", ...)`
3. Run: `./dev.py test front-transaction tx-{concern}`

### Key functions

| Function | Module | Purpose |
|----------|--------|---------|
| `_run_playwright(spec_file, ...)` | `_frontend_common.py` | Runs a Playwright spec file |
| `_ensure_db_populated()` | `_frontend_common.py` | Calls `db populate --force` before tests |
| `_ensure_test_users()` | `_frontend_common.py` | Creates 8 E2E test users |
| `_ensure_frontend_build()` | `_frontend_common.py` | Builds frontend if stale |
| `add_test(cat, action, func, ...)` | `_common.py` | Registers a test in the category dict |
| `_run_test_suite(tests, ...)` | `_common.py` | Runs a list of tests with summary |

