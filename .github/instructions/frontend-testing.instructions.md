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
```bash
# All frontend at once
./dev.py test all-frontend

# Options: --ui (Playwright UI), --headed (visible browser), --debug (debug mode)
./dev.py test front-transaction tx-broker-access --headed
```

## Resume Interrupted Runs

When a test fails mid-suite, fix the issue and resume from where it stopped:

```bash
./dev.py test --resume all-frontend              # Skip already-passed categories
./dev.py test --resume front-transaction all     # Skip passed tests within category

./dev.py test --run-status                       # Show cache state
./dev.py test --fresh-run all-frontend           # Clear cache + run from scratch
./dev.py test --fresh-run                        # Just clear cache (no run)
```

**How it works**:
- Cache: `scripts/test_runner/.run_cache.json` (gitignored)
- Each suite tracks passed test names; `--resume` skips them
- When entire suite passes: cache auto-clears (cycle complete)
- `--fresh-run`: explicitly clears all cached state

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

## ⛔ The three rules — normative

Specs share **one database** and **one backend** with every other spec, and will
increasingly share it *concurrently*. A spec that assumes it is alone is not
simpler — it is broken, and running one worker was only hiding it.

### 1. Never locate by position

A bare `.first()`, `.nth(0)`, "the first row". Another spec creates a record, the
sort order shifts, and the click lands somewhere else.

```ts
// ✘ whatever the DOM happens to put first
await page.getByTestId('asset-row').first().click();

// ✔ filtered to the row this spec created
const name = `E2E asset ${Date.now()}`;
await page.getByTestId('asset-row').filter({ hasText: name }).click();
```

`.first()` is fine **on an already-filtered locator**, where it resolves to one
element by construction. It is the *unfiltered* `.first()` that is the defect.

If the table pages, walk the pages until the row is found and fail with a message
saying so. Do not assert on page 1.

### 2. Never assert a count you did not create

```ts
// ✘ a neighbour adding one row breaks this
await expect(page.getByTestId('asset-row')).toHaveCount(4);

// ✔ says what it means
await expect(page.getByTestId('asset-row').filter({ hasText: name })).toHaveCount(1);
```

### 3. Never wait on the clock

`waitForTimeout()` is **forbidden** in new specs. It is a bet on machine speed
that concurrency loses.

```ts
// ✘ — and note the trap: this waits for the field to exist, not to be filled
await page.waitForTimeout(2000);
await expect(input).toBeVisible();

// ✔ wait for the condition that actually matters
await expect(input).not.toHaveValue('');
```

The real case this comes from (W9, `transfer-same-currency`): the comment said
*"wait for WAC value to populate"*, the code waited for visibility, the blur then
fired against an empty field and flipped the mode. The spec did not find a bug —
**it created the condition it then reported.**

### 4. If there is nothing to wait for, the product is missing a state

Do not hunt for a cleverer selector. If no observable signal says the operation
finished, the **user** cannot tell either. Make the state explicit in the
component (`idle | pending | done | error`), surface it, and have the spec read
the same attribute. One change, two beneficiaries. **If the right way to surface
it isn't obvious, stop and ask** — it is an interface decision.

Two worked examples from this tree, both found by asking *why* a sleep was there:

```ts
// ✘ the list page loads in two waves — rows first, prices after — and said so nowhere
await page.waitForSelector('[data-testid="assets-page"]');
await page.waitForTimeout(1000);      // "wait for loading to complete (skeleton → content)"

// ✔ the page now reports the state it already had
await page.waitForSelector('[data-testid="assets-page"][data-busy="false"]');
```

The second is worth reading twice, because the signal existed and **was lying**:
`ImageEditModal` sets `data-cropper-ready` as soon as it can paint, then keeps
discarding change events for another ~500 ms while it runs its own reset. Edits
made in that window vanish — for the spec *and for the user*, who can close the
modal and lose them with no warning. The spec slept 1500 ms; the fix was to
publish the state that decides (`data-edit-ready`), not to sleep longer.

**The tell is in the comment.** When you catch yourself writing *"extra settle
time"*, *"let it load"*, *"wait for X to finish"* — you have just named a state
the product does not expose. Publish it.

> When a spec fails and the cause is not obvious, use the **`test-triage`** skill.
> First hypothesis is always *"was it the shape of the response?"*. **`flaky` is
> not a verdict.**

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

