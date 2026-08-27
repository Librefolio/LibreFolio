---
applyTo: "frontend/e2e/**,frontend/src/**/*.test.ts"
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

## Component tests (Vitest + jsdom)

Not everything belongs in a browser. A component that only maps props to DOM and
calls back — a calendar grid, a chip input, a column filter — can be mounted in a
simulated DOM and driven directly, in milliseconds, with no login, no navigation
and no shared database. Reaching the same surface through Playwright means
asserting on a component two levels below the one under test, and paying seconds
for the privilege.

**Where the line falls:**

| write a component test | write an E2E |
|---|---|
| props in, DOM out, callbacks out | anything that crosses the API |
| keyboard/interaction models (arrows, Enter, Escape) | anything that depends on seeded data |
| state that is hard to reach from a page (empty, disabled, error) | the flow a user actually performs |
| a UI primitive shared by many pages | the page that composes them |

**The infrastructure, already wired:**

- `frontend/vitest.config.ts` — `svelte()` + `svelteTesting()` plugins. The default
  environment stays `node` so the ~650 existing unit tests do not pay for jsdom.
- `frontend/src/__tests__/component.ts` — the shared harness. Exports `render`,
  `screen`, `fireEvent`, `within`, `waitFor`, `cleanup` and `setupI18n()`; imports
  the jest-dom matchers and stubs `scrollIntoView` (jsdom has no layout engine).
  The directory is excluded from coverage, so the harness never inflates the
  numbers it exists to improve.
- `$test` → `src/__tests__`, declared in `svelte.config.js` — **not** in
  `tsconfig.json`, which SvelteKit regenerates.

**The shape of a spec** (references: `ui/date/CalendarMonth.test.ts`,
`ui/input/TagInput.test.ts`):

```ts
// @vitest-environment jsdom   ← first line, mandatory, per file
import {describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n} from '$test/component';
import Thing from './Thing.svelte';
```

Call `await setupI18n()` in `beforeAll` when the component reads `$_(...)`:
`register()` loads the catalogues through dynamic `import()`, so without awaiting
it the first render can land while the dictionary is still empty and every label
renders as its own key — a flake by construction.

**Most components here are controlled**: they never mutate `value`, they call
`onchange(next)` and wait to be re-rendered. Assert on the call — that is the
contract — and use `rerender` only when the follow-up state is the subject.

**The rules below apply unchanged.** In particular: never assert on translated
text (supply `weekdayLabels`/`monthLabels` as props and assert on those), and
never use a CSS class as a semantic selector. If the visual state has no stable
handle, the component should publish one — `CalendarMonth` gained
`data-state="selected|range-start|in-range|today|…"` for exactly this reason, and
`data-testid`/`data-state` are additive attributes that change no behaviour.

Register new files in `front_component_unit` in
`scripts/test_runner/_frontend_utility.py` (action `component-unit`).
`./dev.py test check-orphans` covers `frontend/src/**/*.test.ts` too.

## ⛔ The rules — normative

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

**The same trap without a sleep: a section that isn't there yet.** When a block is
rendered conditionally on data that arrives asynchronously, its absence means
**two different things** — the feature is unsupported, or the fetch hasn't landed.
Waiting for the section to appear therefore asks *"has the network finished?"*
while looking like it asks *"is this supported?"*. `RiskAnalysisPanel` hides every
section behind a capability catalog and now publishes `data-catalog="pending|ready"`;
the spec waits on that, and a section still missing afterwards is a real red.

```ts
// ✘ green at 1 worker, red at 4 — and the red looks like a broken feature
await expect(page.getByTestId('risk-comparison-controls')).toBeVisible({timeout: 12_000});

// ✔ ask whether the gate has opened, then assert on what's behind it
await expect(page.getByTestId('risk-analysis-panel')).toHaveAttribute('data-catalog', 'ready');
await expect(page.getByTestId('risk-comparison-controls')).toBeVisible();
```

### 5. Never assert on translated text

The UI ships in EN/IT/FR/ES. Any assertion on a user-facing string is a bet on
the active locale.

```ts
// ✘ breaks the day someone runs the suite in Italian
await expect(page.getByText('Import completed')).toBeVisible();

// ✔ the variant is a contract; the text is not
await expect(page.getByTestId('toast-success')).toBeVisible();

// ✔ better still, the structured half of the same notification
const since = await eventSeq(page);
await commitButton.click();
const ev = await waitForEvent(page, 'tx.import.committed', {since});
expect(ev.detail.imported).toBe(47);
```

This is why an event exists **even when a toast exists**: the toast is the human
half, the event is the machine half, and only one of them is safe to assert on.
Helpers live in `e2e/fixtures/app-events.ts`, the product side in
`$lib/stores/app/notify.svelte.ts`.

`waitForSettled(page)` is the third helper: it reads `data-busy` on the nearest
container and returns when the page says every load wave is in.

### 6. Never let a probe decide whether to act

A conditional with a short timeout does not ask "is this here?" — it asks "is
this here *within 1 s*?". Under four workers the honest answer is often no, and
then the spec skips its own setup **in silence** and fails somewhere else
entirely.

```ts
// ✘ turns "slow" into "absent", then carries on as if nothing happened
if (await field.isVisible({timeout: 1000}).catch(() => false)) {
    await field.fill('changed');
}
await expect(saveButton).toBeEnabled();   // fails: the form was never dirtied

// ✔ if the field is genuinely always there, say so and let the timeout speak
await expect(field).toBeVisible({timeout: 5_000});
await field.fill('changed');
```

Before writing the conditional, check the component: if the element is always
rendered on that path, the defensiveness is not caution — it is a silencer.
Real case: `tx-commit-all-types`, where `TransactionFormModal` always renders
the section the spec was tiptoeing around.

### 7. Verify the precondition, do not assume it

Related to rule 1 but distinct: filtering to the *right kind* of row is not the
same as filtering to a row that can still do what you need. A neighbouring spec
may have already consumed it.

```ts
// ✘ paired is necessary, not sufficient — someone may have split this one already
const rowId = await findPairedRowId(page);
await openMenu(rowId);
await page.getByTestId('context-menu-action-split').click();   // never appears

// ✔ scan candidates and keep the first that actually offers the action
const rowId = await findSplittableRowId(page);
```

The general form: **if the spec depends on a state it did not create, it must
check for that state, not infer it.** The alternative — demanding exclusive
access — is a real option, but it costs the whole suite parallelism and has to
be justified in writing.

## Parallelism

`fullyParallel` is **`true`**, and the unit of parallelism is the *test*, not the
file. Concurrency is the default; a block that genuinely shares state **opts
out** and says why.

```ts
test.describe.configure({mode: 'serial'});   // + a comment naming what is shared
```

This is the frontend twin of the backend catalogue's `exclusive_because=`. The
default flipped only after every non-gallery category was run at four workers
until it was green — the reds were fixed, not declared away.

| backend | frontend |
|---|---|
| `isolation=WRITE_SCOPED` (the norm) | nothing to write: parallel is the default |
| `exclusive_because="…"` | `mode: 'serial'` **with a written reason** |

Current exceptions, and they are the whole list: `brokers/multi-user.spec.ts`
(two browser contexts shared across tests) and `tx-brim-import.spec.ts` (the two
sample BRIM files, whose parse rewrites their metadata). `asset-event-delete`
used to be a third until its first test stopped eating the fixture and started
creating the event it deletes — which is the shape a fix should usually take.

!!! warning "There is no flag to un-serialise a block"

    `E2E_FORCE_PARALLEL` is obsolete — it set `fullyParallel`, which no longer
    needs setting, and Playwright offers no config override for a describe-level
    `mode`. Re-testing an exception is a source edit: comment the declaration
    out, run the category at four workers, then delete it with the run as
    evidence or restore it with the reason updated.

!!! danger "Anything that resets shared state must check the worker count"

    A worker now interleaves tests from many files, so "clean up what appeared
    since I opened this file" also covers rows another worker is still using. The
    transaction-hygiene fixture disables itself above one worker for exactly this
    reason (`e2e/fixtures/playwright.ts`). Any new cleanup must do the same, or
    be scoped to ids the test itself created.

Measured through the runner at `--workers 4`: `front-transaction` 16,7 min → 5,6
min, `front-fx` 3,2 → 1,4, `front-asset` → 2,3. Every red exposed along the way
was a defect in a spec or in the product — none was a genuine write conflict.

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

