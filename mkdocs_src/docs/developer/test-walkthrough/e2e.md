# 🎯 End-to-End Tests (`e2e`)

These tests verify the full application stack, from the frontend UI down to the database.

## 🎯 Purpose

To ensure that user flows (e.g., logging in, viewing the dashboard) work correctly in a real browser environment.

## ✅ Prerequisites

None to arrange by hand: the runner starts the backend and the frontend build for you. The one thing
to check is that **port 6041 is free** — `lsof -ti:6041` must come back empty.

## 🔑 Key Tests

- **Login Flow**: Verifies that a user can log in and is redirected to the dashboard.
- **Dashboard**: Verifies that the dashboard loads and displays data.

## 🚀 Running

```bash
./dev.py test front-transaction all      # one domain
./dev.py test all-frontend               # everything
```

## ⛔ The semantics: verify, never assume

Every spec shares **one database and one backend** with every other spec, and increasingly shares
them *at the same time*. A spec that assumes it is alone is not simpler — it is broken, and running
one worker was only hiding it. The normative form of the rules lives in
`.github/instructions/frontend-testing.instructions.md`; what follows is why they exist.

### Position

Never `.first()` on an unfiltered locator, never `.nth(0)`, never "the first row". Filter to
something **the spec itself created** — a name carrying a timestamp — and if the table pages, walk
the pages until you find it. `.first()` on an already-filtered locator is fine: it resolves to one
element by construction.

### Count

`toHaveCount(4)` is a claim about everyone else's data. `toHaveCount(1)` on a locator filtered to
your own row is a claim about yours.

### Time

`waitForTimeout()` is forbidden. It is a bet on machine speed that concurrency loses, and it is the
single largest source of dead time in the suite — 885 calls declaring **410 seconds of sleep per
run** when they were first counted.

Wait for the condition that matters, not for the clock:

```ts
// ✘ waits for the field to exist, not to be filled
await page.waitForTimeout(2000);
await expect(input).toBeVisible();

// ✔
await expect(input).not.toHaveValue('');
```

### And when there is nothing to wait for

That is the interesting case, and it is **not** a prompt to find a cleverer selector. If no
observable signal says the operation finished, the **user** cannot tell either: the sleep is the
symptom, the diagnosis is that a state of the system is invisible.

The fix serves both at once — publish the state the component already has:

```svelte
<!-- the list loads in two waves: rows first, then prices per row -->
<div data-testid="assets-page" aria-busy={busy} data-busy={busy ? 'true' : 'false'}>
```

```ts
await page.waitForSelector('[data-testid="assets-page"][data-busy="false"]');
```

The same contract exists for **charts**. ECharts emits `finished` when a render pass —
animations included — completes, but nothing in the DOM says so. `attachChartReady()`
(`frontend/src/lib/utils/chartReady.ts`) publishes it on the chart container:
`data-chart-ready` flips to `'true'` after the first render, and `data-chart-renders` counts
completed passes so a *re*-render (new range, new series) can be awaited without a stale
`true` letting the reader through too early.

On the spec side, `expectChartCanvas(page, testId)` (`frontend/e2e/fixtures/charts.ts`)
asserts the container holds a **rendered** chart — container and `<canvas>` visible, non-zero
CSS box *and* non-zero bitmap — with both size checks under `expect.poll` because ECharts
attaches and sizes the canvas asynchronously after mount. Asserting the container alone stays
green while ECharts never draws inside it; that is the exact regression shape this helper
exists to catch.

!!! warning "A signal can exist and still be lying"

    `ImageEditModal` sets `data-cropper-ready` as soon as the cropper can paint — but the modal
    keeps **discarding change events for another ~500 ms** while it runs its own reset pass. Edits
    made in that window disappear, for the spec and for the user, who can then close the modal and
    lose them without a warning. The spec had answered with `waitForTimeout(1500)`. The fix was to
    publish the state that actually decides (`data-edit-ready`), not to sleep longer.

    When you write *"extra settle time"*, *"let it load"*, *"wait for X to finish"* in a comment,
    you have just named a state the product does not expose.

## 🧵 Parallelism: earned, not assumed

The suite runs **fully parallel**, and the unit of parallelism is the *test*, not the file: one
worker interleaves tests from many spec files against one backend and one database. That was not
the starting point — it was earned, category by category, by running each at four workers until it
was green and fixing what came out.

```bash
./dev.py test --workers 4 front-fx all      # the runner decides E2E_WORKERS for Playwright
```

| what | means |
|---|---|
| `--workers N` | how many browsers. The backend follows: **one uvicorn worker per two browsers**, never fewer than one |
| `fullyParallel: true` | the default. Tests are distributed individually; a worker does not own a file |
| `test.describe.configure({mode: 'serial'})` | this block opts **out** — **and says why in a comment** |

The order that got us here still applies to any new area: first run it parallel, then read the reds,
then fix them, and only then declare an exception. A declaration added without a run behind it is a
guess with better syntax.

!!! warning "`E2E_FORCE_PARALLEL` is gone"

    It existed to override `fullyParallel: false`, which no longer exists. And it never could have
    overridden a `mode: 'serial'` block — Playwright gives the config no such knob. Re-testing an
    exception means commenting its declaration out, running the category, and deciding with the
    result in hand.

### What the reds actually turned out to be

Across every category promoted, **not one red was a write conflict between two specs**. They were
all specs asking a question whose answer happened to be stable at one worker:

- *"is it on the first page?"* asked as if it meant *"does it exist?"* — the tables paginate
  client-side over the whole dataset, so a neighbour's row changes the answer;
- *"has it finished?"* asked with `waitForTimeout` — a bet on machine speed that four workers lose;
- *"did the write succeed?"* asked as `response.ok()` — `POST /transactions/commit` answers **200
  with a rolled-back batch** when a business rule fails, and reports the ids the rows *would* have
  had. Check `committed`, and treat per-item `status: "simulated"` as "this row does not exist";
- *"is the row still gone?"* asked by id — SQLite reuses the highest rowid the moment you delete it,
  so an id you freed is very likely already someone else's row. Assert absence on a marker **you**
  generated;
- *"do I still own this position?"* asked by selling a fixture holding — `SELL create → commit` sold
  a quantity a neighbour had already consumed. A test that needs a precondition creates it: the
  batch now deposits, buys and sells in one commit;
- *"is this feature supported?"* asked by looking for the section that a capability catalog gates —
  the section is absent while the catalog is in flight too, so the question silently became *"has
  the fetch landed yet?"*. The panel now publishes `data-catalog="pending|ready"` and the test waits
  on that instead.

!!! danger "A conditional render driven by a fetch must publish that the fetch landed"

    This one is a product defect, not a test defect. Whenever `{#if someCapability}` depends on data
    that arrives asynchronously, **absence has two meanings** — "not supported" and "not loaded yet"
    — and nothing in the DOM separates them. Every observer, test or human, is then measuring
    network latency and calling it functionality. Publish the distinction (`data-catalog`,
    `data-busy`, a skeleton) and the ambiguity disappears for everyone.

### Cleanup is where interleaving bites hardest

A fixture that deletes "everything created since I opened this file" was correct exactly while a
worker owned the file from start to finish. It no longer does, so the same sentence now describes
**another worker's in-flight rows** — and the repopulate path would wipe the database under three
running tests. `e2e/fixtures/playwright.ts` therefore disables transaction hygiene above one worker,
and any new cleanup must either do the same or delete only ids the test itself created.

### Staying serial is a legitimate answer — but it is the second-best one

`multi-user.spec.ts` shares two browser contexts across its tests. `tx-brim-import.spec.ts` parses
the same two sample files in every test, and parsing rewrites the file's metadata JSON. Neither is
fixable with a better timeout, and both say so in a comment above the declaration — the frontend
twin of the backend catalogue's `exclusive_because`.

`asset-event-delete.spec.ts` was the third, and is the instructive one. Its first test deleted one
of Apple's two *unlinked* mock events, so it worked exactly twice: on the third run the oldest row
was a linked event, the API answered `in_use`, and the suite went red for a reason unrelated to any
code change. Serialising the block hid the interference but not the expiry date. The test now
creates the event it deletes, and the declaration is gone.

> A test that consumes fixture data is a test with an expiry date. Declaring it serial buys time;
> making it create what it needs removes the problem.

## 🛡️ The CSP collector {: #csp-collector }

A managed instance sends a report-only Content-Security-Policy on the web app's pages: nothing is
blocked, and the browser lists each violation in its console, where nobody reads it. Each one is
something an enforced policy would block. The **collector** (lot H-43) turns them into reds:
`cspViolations`, an automatic, test-scoped fixture of `e2e/fixtures/playwright.ts`, which every spec
imports, records the violations of the test's pages and fails the test on any that the baseline
does not know. Its pure logic is in `e2e/fixtures/csp.ts` (`cspCollectorEnabled`, `isKnown`,
`loadBaseline`).

### 🧾 What it records

- **Every page of the test's context.** Before the test, the fixture adds to the test's browser
  context an init script, which listens for `securitypolicyviolation` on `document` in the capture
  phase, and a binding, `__lfCspViolation`, which the listener calls. Both belong to the context, so
  every page of it, its frames and every navigation are covered. The pages of a context the test
  creates itself (`browser.newContext()`) are not.
- **Each violation as the page saw it**, with the URL of the page it came from: `directive` (the
  effective one), `violatedDirective`, `blockedURI`, `sourceFile`, `lineNumber`, `columnNumber`,
  `sample`, `disposition` (`enforce` or `report`), `documentURI` and `page`.
- **At teardown**, one round trip through each open page lets a report still on its way land. When
  anything was recorded, the list is attached to the test as `csp-violations` (JSON). Then, while
  the option `cspFailOnUnknown` is on (the default), a violation the baseline does not know fails
  the test, one readable line each: directive, blocked URI, source file and line, page, disposition.
- **Readable by the test.** A test that asks for the fixture gets `cspViolations.list()`, every
  violation so far, and `cspViolations.unknown()`, those the baseline does not know.

What there is to record depends on the lane:

- **Every lane, self-hosted or managed**, sends the enforced policy on the web app's pages
  (`web_app_policy()` in `backend/app/services/platform/security_headers.py`, see
  [Frame Protection and the Report-Only Policy](../architecture/security.md#managed-headers)), with
  the hashes of the build's inline scripts, so the app's own inline scripts report nothing. What the
  collector records there are violations with disposition `enforce`: what the browser really
  blocked.
- **Where `LIBREFOLIO_CSP_REPORT_ONLY` is on** (the managed profile's default; a self-hosted lane
  can set it with `--lane-setting`, see [Lane Settings](index.md#lane-settings)), the pages also
  carry `Content-Security-Policy-Report-Only` with `CSP_REPORT_ONLY_POLICY`, the whole policy the
  app aims at. Its violations, disposition `report`, are what that stricter policy would block.
- A spec may add a policy of its own (`layout/page-policy.spec.ts`, `layout/csp-collector.spec.ts`).

### 📒 The baseline {: #csp-baseline }

`frontend/e2e/csp-baseline.json` lists the violations already known, each entry with an `id`, a
`directive`, the blocked resource, an optional `sample`, a `reason` and an `owner`. An entry knows
a violation of its directive through three keys:

- `blockedURI`: the violation's blocked URI, equal (`inline`, `eval`, an address);
- `blockedPath`: the path of the blocked address, whole, whatever its origin and query, for an
  address the user typed. A blocked URI that is not an absolute URL (`inline`, `eval`) never
  matches it;
- `sample`, optional: the violation's sample, equal. The policy has `'report-sample'`, so
  Chromium reports the first 40 characters of a blocked script or `eval`; an entry without
  `sample` knows the violation whatever its sample.

An entry has exactly one of `blockedURI` and `blockedPath`. The app's own inline scripts need no
entry: the policy allows them by their hashes (lot H-52).

One entry today:

| `id` | Matches | The violation, and who cures it |
|------|---------|---------------------------------|
| `cheetah-grid-global-probe` | `script-src`, `eval`, `sample` `(function anonymous(\n) {\nreturn this\n})` (`\n` a line break) | cheetah-grid's bundled webpack probe of the global object, `new Function("return this")()`, inside a `try`/`catch` that falls back to `window`: harmless under an enforced policy. Found by the first cloud smoke in the BRIM table preview (`files.spec.ts`). The sample is the source Chromium reports for `new Function("return this")`, and any other `eval` fails a test. Coverage builds are not concerned: istanbul reaches the global object through `globalThis`, not through `new Function`. Removed when cheetah-grid stops probing the global object with `eval` (an upgrade, or a bundler that rewrites the probe) |

The address check of a link no longer needs an entry: it loads an image (`GET /api/v1/auth/address-probe.png`), and `img-src` is not enforced, see [The Address Check Is an Image](../architecture/security.md#csp-address-probe).

The baseline is a ratchet: an entry is added only by a recorded decision, with its reason and its
owner, never to silence a red, and removed by the lot that cures it.

### 🔌 The kill switch

`E2E_CSP_COLLECTOR=0` in the environment of a run turns the collector off for the whole run: no
binding, nothing recorded, nothing failed. Give it to one run, on its command line:

```bash
E2E_CSP_COLLECTOR=0 ./dev.py test front-utility csp-collector   # the run where the kill-switch test runs
```

Never put it in `.env.example`: a lane's cleanup removes every variable that file documents, so
the switch would no longer reach Playwright.

### 🚨 When the collector fails a test

1. Read the test's `csp-violations` attachment in the report: each violation with its directive,
   blocked URI, source file, line and page, and for a blocked script or `eval` its sample, the
   first 40 characters of the code.
2. Fix the page. A real fix changes what the app does (a script moved to a file, a resource served
   from the app's own origin), and the violation is gone. An inline `<script>` in a page of the
   build is allowed by its hash, which the server computes when it starts: after a new build,
   restart the server. An inline event handler (`onclick="…"`) is `script-src-attr`, which no hash
   covers: listen from the page's script instead, as `frontend/static/offline.html` does. The gate `frontend/src/noInlineEventHandlers.gate.test.ts` (Vitest) fails on any inline `on…="…"` attribute in the source, `src/app.html` included; icon fallbacks go through the attributes `data-hide-on-error`, `data-fallback-text` and `data-fallbacks`, handled by `frontend/src/lib/features/security/imageErrorFallback.ts`.
3. Add a baseline entry only by a recorded decision: the violation understood, its `reason`
   written, its `owner` the lot that will cure it.
4. `test.use({cspFailOnUnknown: false})` belongs only to a test whose subject is the violations
   themselves, never to silence a red. Two specs use it today, each in a nested `describe`: the
   collector's own (`e2e/layout/csp-collector.spec.ts`), for its two tests that record an unknown
   violation without failing on it, and `e2e/layout/page-policy.spec.ts`, for its positive-control
   test, which raises three enforced violations on purpose (`base-uri`, `object-src`,
   `form-action`) and checks them itself. The collector still records and attaches what they
   raise.

The collector's own tests and the cloud smoke, the main specs on a managed lane, are actions of
`front-utility`: see [CSP Collector](front-utility.md#csp-collector) and
[Cloud Smoke](front-utility.md#cloud-smoke).

## 🔍 When a spec fails

Use the **`test-triage`** skill. Its first hypothesis is *"was it the shape of the response?"* —
the data was there but elsewhere, the page held something else, the count differed. **`flaky` is not
a verdict.**
