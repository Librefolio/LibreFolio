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

# With coverage tracking — Python + JS/Svelte (default when the language is omitted)
./dev.py test --coverage front-transaction all

# Only one language
./dev.py test --coverage py front-transaction all    # backend Python only
./dev.py test --coverage js front-transaction all    # frontend JS/Svelte only

# Gallery screenshots
./dev.py mkdocs gallery
./dev.py mkdocs gallery --desktop-only
./dev.py mkdocs gallery -f "assets"
./dev.py mkdocs gallery -l              # list available tests
```

### Consolidation is on by default

A category no longer launches one Playwright process per action. `_consolidate.py` groups every unit
of a category by `(category, project)` and launches **one** invocation per group — 8 categories go
from roughly 120 invocations to 16 — with the database populated and the users created **once** for
the whole run rather than once per action.

```bash
./dev.py test --no-consolidate front-fx all   # the old one-process-per-action route
./dev.py test --no-fail-fast all-frontend     # run everything, report every red
```

`--no-consolidate` exists as the escape hatch, not as the recommended path: the consolidated route is
what the 8 categories are verified against (629 Playwright + 687 vitest passing).

!!! warning "Under `--coverage js` the groups are split into batches of 8"
    A consolidated worker accumulates V8 coverage for its whole lifetime. Measured: 8 specs finish
    comfortably, 25 specs die at the heap limit — and the failure lands on an innocent test with a
    duration of `0ms`. So with JS coverage on, a group runs in batches of `_JS_COVERAGE_CHUNK` (8)
    specs. If a run starts dying again, lower that constant; do **not** raise
    `--max-old-space-size`, which only postpones the crash.

!!! warning "Never run two Playwright invocations at once"
    Consolidation reduces the number of invocations; it does not make them concurrent. They share one
    backend, one database and one set of E2E users, so a second simultaneous invocation corrupts
    both. Frontend parallelism lives **inside** Playwright (`fullyParallel`), never above it.

## Playwright Config

- **2 projects**: `desktop` (1280×720, Chrome) + `mobile` (iPhone 14 Pro Max viewport, Chromium)
- **Workers**: 1 (sequential — shared DB state)
- **Timeout**: 15s per test (localhost — fast responses expected)
- **Web Server auto-start**: `./dev.py server --test --force` (port 6041)
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

Report: `htmlcov-backend-e2e/` (formerly `htmlcov-frontend/` — the old name suggested
it measured frontend code, which it never did).

## JS/Svelte Coverage during E2E

Collected via Chromium V8 (`page.coverage`) and remapped to `.svelte`/`.ts` through
the build's sourcemaps. Enabled by `--coverage js|all`, which sets `COVERAGE_JS=1`.

**All specs must import from the barrel, not from `@playwright/test`:**

```typescript
import {test, expect} from '../fixtures/playwright';
import type {Page} from '../fixtures/playwright';
```

`e2e/fixtures/playwright.ts` re-exports the same symbols and adds an `auto` fixture
that collects coverage only when the flag is on — at flag off the cost is zero.

Key files:
- `frontend/mcr.shared.js`: filters + external sourcemap resolution (read from `build/`)
- `frontend/mcr.e2e.config.js`: E2E config — `cleanCache: false`, the fixture only calls `add()`
- `frontend/scripts/mcr-generate.js`: turns the accumulated cache into the report

Reports: `frontend/coverage-js/e2e/`, merged with the vitest level into
`frontend/coverage-js/combined/`. Open with `./dev.py test coverage show js`.

### The cleaning flags, and why there are only three

| Flag | What it actually deletes |
|---|---|
| `--cov-clean-backend` | `htmlcov-backend` + `.coverage_data/backend` — Python from backend suites |
| `--cov-clean-backend-e2e` | `htmlcov-backend-e2e` + `.coverage_data/frontend` — **Python** from E2E runs |
| `--cov-clean-js` | `frontend/coverage-js/` — the JS/Svelte data |

`--cov-clean-frontend` still works as a deprecated alias for `--cov-clean-backend-e2e`; it was the
last thing in the system calling a Python measurement "frontend".

`--cov-clean-js` is a **manual convenience only**. During any run with `--coverage js|all` the JS
directories are wiped unconditionally anyway, because V8 offsets belong to one specific bundle: kept
across a rebuild they would be remapped onto moved sources and the report would lie without failing.
There is no separate flag for vitest — its data lives in `coverage-js/unit/`, under the same roof.

> **No blocking thresholds**: Svelte 5 compiles templates into closures, so the data
> is reliable about *"was this component reached"*, less so per-line.

### Finding the gaps

```bash
./dev.py test coverage-report --lang js --summary            # counts by category
./dev.py test coverage-report --lang js --category js_store  # detail for one area
./dev.py test coverage-report --lang js --priority high --json
```

Same analyser as the backend (`scripts/coverage_analysis.py`); `scripts/coverage_js.py`
converts monocart's istanbul JSON and supplies the frontend categories
(`JS_FEATURE`, `JS_STORE`, `JS_API`, `JS_UTILITY`, `JS_CHART`, `SVELTE_UI`, `JS_ROUTE`, …).

Two caveats when reading it:

- `.svelte` entries are named `block@142` — the compiler leaves closures anonymous. The
  `.ts` sections (`JS_UTILITY`, `JS_STORE`) carry real names and are the best starting point.
- Statements are attributed to functions **by line range**, so a nested closure counts
  twice. Use it to rank untested code, not to quote a percentage.

## Conventions

- **`data-testid` always**: never select by CSS class or text (fragile with i18n)
- **Explicit timeouts**: use `{timeout: N}` on expect/waitFor — keep them tight (localhost is fast)
- **Never skip for missing data**: if mock data is needed, ensure it exists in `populate_mock_data.py`
- **Mobile awareness**: handle hamburger menu with `openMobileMenu()`
- **No hardcoded login**: always use `login()` from `auth-helpers.ts`
- **Request interception**: use `page.waitForRequest()` to verify commit payloads
- **Whoever commits, cleans up**: see below — a spec that writes must restore what it wrote
- **Never `waitForTimeout()`**: see below — it is a bet on machine speed that concurrency loses
- **Never assert on translated text**: assert the toast *variant* (`toast-success`) or the event, never the message
- **Never let a probe decide whether to act**: a short-timeout `isVisible().catch(() => false)` turns *slow* into *absent* and skips the spec's own setup in silence
- **Verify the precondition, do not infer it**: filtering to the right *kind* of row is not the same as finding one that can still do what you need

### ⚠️ Parallelism is the default; serialisation is opted out of

`fullyParallel` is **`true`**, and the unit is the *test*, not the file: one worker interleaves
tests from many spec files against one shared backend and database. A block that genuinely shares
state opts **out**, and says what it shares:

```ts
test.describe.configure({mode: 'serial'});   // + a comment naming the shared resource
```

The twin of the backend's `exclusive_because`. The whole exception list today: `multi-user.spec.ts`
and `tx-brim-import.spec.ts`. `asset-event-delete.spec.ts` was a third until its first test stopped
consuming a mock event and started creating the one it deletes — prefer that fix to a declaration.

`E2E_FORCE_PARALLEL` is **obsolete** — it only set `fullyParallel`, and Playwright has no config
override for a describe-level `mode`. Re-testing an exception is a source edit: comment the
declaration out, run the category at `--workers 4`, then delete it with the run as evidence.

**Cleanup code must check the worker count.** "Delete what appeared since I opened this file" is
only true when a worker owns the file, which is no longer the case: it would delete rows another
worker is mid-test with. The tx-hygiene fixture disables itself above one worker for that reason.

Measured through the runner at `--workers 4`: `front-transaction` 16,7 → 5,6 min, `front-fx` 3,2 →
1,4 min. Every red surfaced along the way was a defect — in a spec, or in the product. None was a
genuine write conflict.

> Note the second kind. `AssetSearchAutocomplete` dropped a query typed before the provider list had
> loaded: the debounce had fired, nothing retried, and the search box just sat there dead. At one
> worker the providers always won the race. Concurrency did not break it — it made a rare condition
> normal.

### ⚠️ Signals: read state, never an edge

`notify()` (`$lib/stores/app/notify.svelte.ts`) records every notable action into a retained ring
buffer, and raises a toast only when the user is owed one. Helpers in `e2e/fixtures/app-events.ts`:

```ts
const since = await eventSeq(page);
await commitButton.click();
const ev = await waitForEvent(page, 'tx.import.committed', {since});
expect(ev.detail.imported).toBe(47);

await waitForSettled(page);   // reads data-busy: every load wave is in
```

Why not `page.on('console')`: a console message is an **edge** — it must be armed before the action,
so a spec that clicks first has already lost it, which is the exact flakiness we are removing. And
`debug` is compiled out of the production build the E2E suite runs against, so it does not exist in
the binary under test. The ring buffer is a **state**: arriving late costs nothing.

### ⚠️ No clock waits — and what to do when there is nothing to wait for

`waitForTimeout()` is forbidden in new specs. Assertions and actions in Playwright already retry to
their own timeout, so a sleep before one is dead weight; a sleep *instead* of one is a guess.

Most removals are mechanical. The interesting case is when there is genuinely no signal to wait
for — and the answer is **not** a cleverer selector:

> If nothing observable says the operation finished, the **user** cannot tell either. The sleep is
> the symptom; the diagnosis is that a state of the system is invisible. Publish it once and both
> get it: an attribute for the spec, `aria-busy`/an indicator for the user.

```svelte
<!-- the list loads in two waves: rows first, then prices per row -->
<div data-testid="assets-page" aria-busy={busy} data-busy={busy ? 'true' : 'false'}>
```

```ts
await page.waitForSelector('[data-testid="assets-page"][data-busy="false"]');
```

A signal can also exist and **be wrong**: `ImageEditModal` set `data-cropper-ready` while it was
still discarding change events for another ~500 ms, so edits made in that window disappeared — for
the spec and for the user, who could close the modal and lose them without a warning.
`data-edit-ready` reports the state that actually decides.

**The tell is in the comment.** *"extra settle time"*, *"let it load"*, *"wait for X to finish"* —
each one names a state the product does not expose. **If how to surface it is not obvious, stop and
ask**: it is an interface decision, not a test detail.

**A section that is not there yet is the same trap without a sleep.** When a block is rendered
conditionally on data fetched at runtime, its absence carries **two meanings at once** — unsupported,
or not loaded yet — so waiting for it to appear asks *"has the network finished?"* while reading like
*"is this supported?"*. `RiskAnalysisPanel` gates every section on a capability catalog and publishes
`data-catalog="pending|ready"`; specs wait on the gate, then assert on what is behind it. Anything
still missing at that point is a genuine red.

### ⚠️ Whoever commits, cleans up

Do **not** assume the database was just populated. It used to be true by accident — one Playwright
process per action, and `globalSetup` re-populated before each one — but once specs share an
invocation, what one spec leaves behind becomes the next one's input.

`Transaction` has no `user_id`: a committed transaction is visible to every later spec. Use
`e2e/fixtures/db-cleanup.ts`:

```ts
import {deleteTransactionsCreatedSince, snapshotTransactionIds} from '../fixtures/db-cleanup';

let txBefore: Set<number>;

test.beforeEach(async ({page}) => {
    await login(page, TEST_USER);
    txBefore = await snapshotTransactionIds(page);   // after login: page.request shares the cookie jar
    await goToTransactions(page);
});

test.afterEach(async ({page}) => {
    await deleteTransactionsCreatedSince(page, txBefore);
});
```

Snapshot the ids and delete the difference — don't delete the ids you *think* you created. The
difference also catches rows created indirectly (the other half of a linked pair, a promoted
transfer), and those are the ones that get forgotten.

Real case: `tx-clone` commits a clone of "the first paired giver row on editable brokers" — which is
the `delete-safe` ETH transfer — and `tx-delete` then asserts no such row survives its own delete.
Neither spec was wrong; the implicit contract between them was.

#### The automatic net, and why it works per file

Under a consolidated run (`LF_TX_HYGIENE=1`, set by `./dev.py test front-transaction all`) the
`txHygiene` fixture in `e2e/fixtures/playwright.ts` does this for every spec without any per-spec
code — but **between spec files, not between tests**.

That distinction is not a detail. Specs are written sequentially: `tx-commit-all-types` commits a BUY
and then sells part of it; `tx-delete` creates a pair in one test and deletes it in the next.
Cleaning between tests breaks those chains — measured on the whole `transactions/` directory, it
turned three reds into five. What consolidation removed was the reset *between files*, so that is
what gets restored and nothing more.

So the explicit `db-cleanup.ts` recipe above is still the right tool when a spec needs finer control
than "restore at the end of the file". The automatic fixture is the floor, not a replacement.

#### If a spec *destroys* mock rows, the fixture repopulates

Dropping what a spec added is only half the invariant. `tx-delete` destroys mock rows by design, and
no API call resurrects a row with its original id and its original half of a linked pair. So
`restore()` compares against the opening snapshot: if a baseline id has vanished it runs the full
`populate_mock_data --force --with-reports`, replays `initGlobalSettings()` (the global settings are
the one part of `globalSetup` that `populate_mock_data` does not recreate) and logs the worker API
context back in, because the users get new ids.

Why it matters: on the database the suite leaves behind, `tx-picker-pagination` fails 4 tests; on a
fresh one it passes 5. With fewer rows its first two clicks land on a linked pair, the bulk modal
auto-opens a form modal, and the tests time out clicking behind a backdrop. The error blames
`tx-form-modal` and never mentions `tx-delete`. Row *deflation*, the mirror of row inflation.

The repopulate costs ~20 s, charged to whichever test triggers it, so the fixture grants
`testInfo.setTimeout(+25 s)` **only when it actually ran** — a blanket increase would mask real
slowness.

## Test Runner Architecture (`scripts/test_runner/`)

All tests are orchestrated by a modular Python test runner, invoked via `./dev.py test`.

```text
scripts/test_runner/
├── _registry.py              # TEST_REGISTRY — single source of truth
├── _inventory.py             # Derives what exists: units, isolation classes, reachability
├── _scheduler.py             # inventory + --workers N → execution plan
├── _executor.py              # Runs a plan; one resource lot per worker
├── _consolidate.py           # Groups a frontend category into one Playwright + one vitest run
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

Every `{domain}_all()` suite is **derived from the registry**, not hand-written. Registering an
action is therefore enough to make it run — "registered but unreachable" is no longer a state that
can exist. (It used to: six registered actions worth ~259 tests were never executed by any `all`.)

### Adding a new frontend test spec

1. Create `frontend/e2e/{domain}/tx-{concern}.spec.ts` (or `{domain}.spec.ts`)
2. In the appropriate `_frontend_{domain}.py`:
   - Add a runner function that calls `_run_playwright("path/to/spec.ts", ...)`
   - Register with `add_test(cat, "action-name", runner_func, ...)`
3. The new action becomes available as `./dev.py test front-{domain} action-name`, **and the `all`
   suite picks it up on its own** — do not add it to a list by hand

### Key functions

| Function | Module | Purpose |
|----------|--------|---------|
| `_run_playwright(spec, ...)` | `_frontend_common.py` | Runs Playwright with ui/headed/debug/coverage flags |
| `_ensure_db_populated()` | `_frontend_common.py` | Calls `db populate --force --with-reports` before tests (memoised per run) |
| `_ensure_test_users()` | `_frontend_common.py` | Creates 8 E2E users if missing (memoised per run); sets `LF_SETUP_DONE=1` once the DB is ready too |
| `_ensure_frontend_build()` | `_frontend_common.py` | Auto-builds frontend if stale (memoised per run) |
| `add_test(cat, action, func, ...)` | `_common.py` | Registers a test entry in a category dict |
| `make_category(help, desc)` | `_common.py` | Creates the `_meta` entry for a new category |
| `_run_test_suite(tests, ...)` | `_common.py` | Runs tests sequentially with summary report |


