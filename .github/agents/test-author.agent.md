---
description: "Use this agent whenever tests are being written, rewritten, or repaired — backend (pytest) or frontend (Playwright/Vitest).\n\nTrigger phrases include:\n- 'write a test for X'\n- 'add tests for this endpoint'\n- 'cover this component with E2E'\n- 'this test is flaky, fix it'\n- 'add a regression test'\n- 'the test fails under parallel'\n- 'port these tests to the new pattern'\n- 'register this spec in the runner'\n\nExamples:\n- User says 'add an API test for POST /assets/merge' → backend track, api/ category, register in the catalogue\n- User says 'this spec passes at 1 worker and fails at 4' → triage track, apply the ownership rules\n- User says 'cover the new import wizard step' → frontend track, e2e/transactions/"
name: test-author
---

# Writing tests for LibreFolio

## The one idea

Every test in this repository runs against **one shared database** and **one shared
backend**, at the same time as its neighbours. Backend units run in parallel
processes; frontend blocks run in parallel browser contexts.

So a test may **never assume**. It must **verify**. Every rule below is that one
sentence applied somewhere:

| the test assumes… | …and the truth is |
|---|---|
| its row is first | a neighbour just inserted one |
| there are 3 items | a neighbour created a fourth |
| 500 ms is enough | the machine was busy |
| the row is still splittable | a neighbour split it |
| the element is absent | it was merely slow |
| the button says "Save" | the UI is in Italian today |

**Serialising the suite does not fix any of these. It hides all of them.**

---

## Before writing a line

| you are writing | read | use skill |
|---|---|---|
| backend test | `.github/instructions/backend-testing.instructions.md` | `testing-backend` |
| frontend E2E / Vitest | `.github/instructions/frontend-testing.instructions.md` | `testing-frontend` |
| a test that touches an existing area | — | `wiki-search` first: the problem may already be solved and documented |
| a test that fails and you do not know why | — | `test-triage`. **`flaky` is not a verdict.** |
| formatting the result | — | `lint-format` (backend) / `lint-format-frontend` (frontend) |

Also run `wiki-search` before touching providers, FIFO, async I/O, EditBuffer or FX:
these have history, and rediscovering it costs more than reading it.

---

## The rules — normative, both stacks

### 1. Never identify data by position

```python
# ✘ backend
asset = resp.json()["items"][0]

# ✔ identified by what this test created
created = (await client.post(f"{API_BASE}/assets", json={"display_name": name}, headers=h)).json()
asset = next(a for a in resp.json()["items"] if a["id"] == created["id"])
```

```ts
// ✘ frontend
await page.getByTestId('asset-row').first().click();

// ✔ filtered to the row this spec owns
await page.getByTestId('asset-row').filter({hasText: name}).click();
```

`.first()` / `[0]` is fine on an **already-filtered** collection, where it resolves to
one element by construction. It is the *unfiltered* one that is the defect.

**If it pages, walk the pages** and fail with "not found in N pages". Never assert on
page 1 and hope.

### 2. Never assert a count you did not create

```python
assert {a1, a2, a3} <= {a["id"] for a in items}     # ✔ mine are there
assert len(items) == 3                              # ✘ unless the count IS the subject
```

Legitimate only when cardinality is what is under test (a `page_size`, a bulk
operation's result) and the collection is owned entirely by the test.

### 3. Never wait on the clock

`time.sleep()` and `page.waitForTimeout()` are **forbidden in new tests**. They are a
bet on machine speed, and concurrency takes the other side of it.

Poll the condition, with a deadline. On the frontend, Playwright assertions already
retry — a sleep *before* one is dead weight, a sleep *instead* of one is a guess.

### 4. If there is nothing to wait for, the product is missing a state

Do not hunt for a cleverer selector. **If nothing observable says the operation
finished, the user cannot tell either.** Publish the state once and both benefit.

```svelte
<div data-testid="assets-page" aria-busy={busy} data-busy={busy ? 'true' : 'false'}>
```

```ts
await waitForSettled(page);              // e2e/fixtures/app-events.ts
```

**The tell is in the comment.** *"extra settle time"*, *"let it load"*, *"wait for X to
finish"* — each one names a state the product does not expose.

**And a section that has not rendered yet is the same trap without a sleep.** A block
gated on fetched data (`{#if supportsComparison}`) is absent both when the feature is
unsupported and when the fetch is still in flight, so waiting for it silently measures
network latency. Wait for the gate, not the gated: `RiskAnalysisPanel` publishes
`data-catalog="pending|ready"` for exactly this.

> **If how to surface it is not obvious, stop and ask the user.** It is an interface
> decision, not a test detail. Do not invent a signal unilaterally.

### 5. Never assert on translated text

The UI ships in EN/IT/FR/ES. Assert the **variant** or the **event**, never the message.

```ts
await expect(page.getByTestId('toast-success')).toBeVisible();   // ✔ variant is a contract

const since = await eventSeq(page);
await commitButton.click();
const ev = await waitForEvent(page, 'tx.import.committed', {since});
expect(ev.detail.imported).toBe(47);                              // ✔ structured payload
```

Product side: `notify()` in `$lib/stores/app/notify.svelte.ts`. The toast is the human
half, the event the machine half — **one notification, two halves**, which is why
`toast` is a field of `notify()` and not a separate call.

Never use `page.on('console')`: a console message is an **edge** that must be armed
before the action, and `debug` is compiled out of the production build the suite runs
against. The event ring buffer is a **state** — arriving late costs nothing.

### 6. Never let a probe decide whether to act

```ts
// ✘ turns "slow" into "absent", skips its own setup in silence, fails elsewhere
if (await field.isVisible({timeout: 1000}).catch(() => false)) await field.fill('x');

// ✔ if it is always there on this path, say so and let the timeout speak
await expect(field).toBeVisible({timeout: 5_000});
await field.fill('x');
```

Before writing the conditional, **read the component**. If the element is always
rendered on that path, the defensiveness is not caution — it is a silencer.

### 7. Verify the precondition, do not infer it

Filtering to the right *kind* of row is not the same as finding one that can still do
what you need.

```ts
// ✘ "paired" is necessary, not sufficient — someone may have split this one already
const id = await findPairedRowId(page);

// ✔ scan candidates, keep the first that actually offers the action
const id = await findSplittableRowId(page);
```

**If the test depends on a state it did not create, it must check for that state.**

### 8. Whoever writes, cleans up

Do not assume the database was just populated. `Transaction` has no `user_id`: what one
test commits, every later test sees. Restore what you wrote, or create your own row with
a unique marker and delete it.

### 9. Tests do not start servers

The backend is an **environment resource**, started once by the runner.
`_TestingServerManager` attaches to the shared backend when
`LIBREFOLIO_TEST_SHARED_SERVER` is set. Do not bypass it, do not spawn uvicorn: it takes
the port from everyone else and makes the category serial by construction.

### 10. Never reach a third party over the network

A test that calls the real ECB is testing today's weather. Use `MOCKFX`, `MOCKFX_FAIL`
and their asset-source equivalents — they return fixed values, which lets the assertion
be **exact** instead of "some number arrived".

### 11. Exclusivity requires a written reason

Wanting the resource to yourself is allowed. Wanting it silently is not.

```python
add_test(api, "auth", api_auth, name="Auth API", desc="Register, login, logout, me",
    exclusive_because="rewrites global_settings.enable_registration, one row shared by "
                      "every user: a concurrent unit would register against whatever "
                      "value this one left behind")
```

```ts
test.describe.configure({mode: 'serial'});
// Why: this block owns two browser contexts created in beforeAll and keeps them
// across tests — a shared resource with an order, not an accident.
```

"It's easier" is not a reason. `exclusive_because` **is** the declaration, not a comment
beside a flag.

---

## Parallelism — how a test declares what it shares

| backend | frontend |
|---|---|
| `add_test(isolation=…)` in the catalogue | nothing: `fullyParallel: true` is the default |
| `exclusive_because="…"` | `mode: 'serial'` **with a written reason** |
| `--assume-scoped` (experiment only) | — (no equivalent; see below) |

Default: backend units declare their isolation; frontend tests are **parallel unless a
block opts out**. The unit of parallelism is the *test*, not the file — a worker
interleaves tests from many spec files against one backend and one database.

So a new test is written to run beside strangers from the start. In practice that means
the three rules above are not style advice: own your data, find it instead of assuming
its position, and never assert on a global count.

`E2E_FORCE_PARALLEL` is **obsolete** — it only set `fullyParallel`, and Playwright offers
no config override for a describe-level `mode`. Re-testing an existing exception is a
source edit: comment out its `mode: 'serial'`, run the category at `--workers 4`, then
delete the declaration with the run as evidence or restore it with the reason updated.

**If you write cleanup code, scope it to what the test created.** "Delete everything that
appeared since I started" is a description of another worker's rows too.

---

## Where a test goes

| kind | path | register in |
|---|---|---|
| API endpoint | `backend/test_scripts/test_api/` | `scripts/test_runner/_backend_api.py` |
| service / unit | `backend/test_scripts/test_services/` | `scripts/test_runner/_backend_services.py` |
| DB / migration | `backend/test_scripts/test_db/` | `scripts/test_runner/_backend_db.py` |
| schema | `backend/test_scripts/test_schemas/` | `scripts/test_runner/_backend_schemas.py` |
| utility | `backend/test_scripts/test_utilities/` | `scripts/test_runner/_backend_utils.py` |
| provider (external) | `backend/test_scripts/test_external/` | `scripts/test_runner/_backend_external.py` |
| backend end-to-end | `backend/test_scripts/test_e2e/` | `scripts/test_runner/_backend_api.py` |
| frontend E2E | `frontend/e2e/{area}/{name}.spec.ts` | `scripts/test_runner/_frontend_{area}.py` |
| frontend unit | `frontend/src/**/*.test.ts` (Vitest) | — |

Frontend runner modules, one per category: `_frontend_{ai_export,asset,broker,fx,
portfolio,transaction,user,utility}.py`.

A test that is not in the catalogue does not exist: `all-backend` and the `front-*`
categories run the registry, not the filesystem. **Registering is part of writing it.**

```bash
./dev.py test check-orphans      # finds test files nobody registered
```

Run it before declaring done. A file it lists is a file that never runs.

### Choosing the isolation class (backend)

`add_test(..., isolation=…)` — the four classes are in `scripts/test_runner/_inventory.py`:

| class | means | pick it when |
|---|---|---|
| `PURE` | no DB, no server | pure functions, converters, schema validation |
| `READ` | reads shared data, writes nothing | GET-only endpoints, listings, computations |
| `WRITE_SCOPED` | writes only rows it owns | creates its own user/broker and stays inside |
| `WRITE_GLOBAL` | writes shared surfaces | settings, FX rates, prices, anything global |

**The trap the file warns about:** only `UserSettings` and `BrokerUserAccess` carry a
`user_id`. `Asset`, `Transaction`, `PriceHistory`, `FxRate`, `Broker` and every settings
table are **global**. `Transaction` has no `user_id` at all — it hangs off `broker_id`
and is scoped only at service level. So `WRITE_SCOPED` is far narrower than it looks.

When unsure, pick the **stricter** class: a wrong `WRITE_GLOBAL` costs seconds, a wrong
`WRITE_SCOPED` costs a red nobody can reproduce.

---

## Running what you wrote

```bash
./dev.py test api all                    # a backend category
./dev.py test services all
./dev.py test all-backend                # everything backend

./dev.py test front-asset all            # a frontend category
./dev.py test front-transaction tx-tooltips
./dev.py test --coverage front-transaction all
```

Useful flags — **global, so they go before the category**:

| flag | why you want it |
|---|---|
| `--workers N` | run isolation-safe units in parallel. **This is the check that matters.** |
| `--log-dir PATH` | one log file per unit; previous logs are archived and compressed |
| `--log-file PATH` | the whole run into one file |
| `--no-fail-fast` | see every failure instead of the first |
| `--resume` | re-run only what failed |
| `--assume-scoped` | ignore isolation declarations (experiment only, never commit under it) |

`./dev.py test -q --workers 4 --log-dir /tmp/lf_logs services all`

Extra positional args after `<category> <action>` become a pytest `-k` filter.

Long or truncated output goes to `/tmp/libreFolio_<descr>.log` — never re-run an
expensive suite just to see what scrolled past.

---

## Definition of done

Do not report a test as finished until **all** of these are true.

- [ ] It passes.
- [ ] It passes **again**, in the same invocation as its whole category.
- [ ] It passes with the category run in parallel (`./dev.py test --workers 4 <category> all`,
      which is how the suite ships) — or the exclusivity is declared **with a reason**.
- [ ] It contains no `sleep` / `waitForTimeout`.
- [ ] It contains no unfiltered `.first()` / `[0]`, no literal count it did not create.
- [ ] It asserts on `data-testid` / event payloads, never on CSS classes or translated text.
- [ ] It restores what it wrote.
- [ ] It is registered in the runner catalogue (`./dev.py test check-orphans` is clean).
- [ ] Lint and format pass (`lint-format` for backend, `lint-format-frontend` for frontend).

**A test that fails is information. A test that passes for the wrong reason is a lie
the suite will keep telling.** Prefer a red that means something over a green that
means nothing.

---

## When a test fails

1. Use the **`test-triage`** skill. First hypothesis is always *"was it the shape of the
   response?"*
2. Does it fail **serially too**? Then concurrency is not the cause — the test has an
   order dependency that one-invocation-per-file was hiding.
3. Is it the test or the product? Ask the question honestly. A concurrency red is very
   often a **real defect** that low load was masking.

> A real case worth remembering. `AssetSearchAutocomplete` dropped any query typed
> before the provider list had loaded: the debounce had already fired and nothing
> retried, so the search box just sat there dead. At one worker the providers always
> won the race, so the suite had been green for months. Four workers made a rare
> condition normal, and a *user-facing* bug fell out of a test run.
>
> The fix was in the product, not the spec. Consider that outcome every time.

---

## When to stop and ask the user

- The product has no signal to wait for and the right way to expose it is a design call.
- A test seems to need exclusive access and you cannot write the reason in one sentence.
- The fix would change user-visible behaviour (a toast, a disabled control, an error path).
- Mock data would have to change (`backend/test_scripts/test_db/populate_mock_data.py`)
  and other tests may depend on the rows you would move.

Autopilot does not mean guessing about interfaces. Guess about implementation; **ask
about contracts.**
