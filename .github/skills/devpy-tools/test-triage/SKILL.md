---
name: test-triage
description: "Use this skill when a LibreFolio test fails and the cause is not obvious — especially when it fails intermittently, fails only in a full run, fails only under --workers > 1, or passes when re-run alone. Gives the ordered list of hypotheses to test, and the evidence to collect for each. Also use it before declaring any red 'flaky'."
---

# Triaging a red test

A failing test tells you *where* the symptom surfaced. It almost never tells you
where the cause is. This protocol is the order in which to ask.

**The rule that makes it work: hypotheses are checked in order, and `flaky` is not
a verdict.** "Flaky" is how this debt reforms — it converts a real defect into a
retry, and the next person inherits both.

---

## 0. Before anything: get the evidence, don't re-run blind

Re-running a red is the slowest possible way to learn about it, and for an
intermittent one it also destroys the state that produced it.

```bash
# One log file per unit, plus the test database as it was, compressed.
./dev.py test --log-dir /tmp/lf-triage all-backend
```

Previous contents are archived into `00_archive/<YYYYMMDD_HHMM>/` rather than
overwritten, so two runs can be compared instead of remembered.

What you now have per red:

| | where | what it answers |
|---|---|---|
| the unit's log | `/tmp/lf-triage/<unit>.log` | what the test saw |
| the database | archived alongside | what the test was looking at |
| the run cache | `./dev.py test --run-status` | what else was running |

Only after reading the log do you re-run — and then with `--resume`, so you
re-run the red and not the 2500 tests that already passed.

---

## 1. First hypothesis: **was it the shape of the response?**

This goes first because in this codebase it is the most common cause and the
easiest to mistake for something else. Ask, in this order:

1. **Was the data there, but somewhere else?** The test asked for `[0]`, or
   `.first()`, or page 1 — and another test created a row that now sorts ahead of
   the one it wanted.
2. **Did the count differ?** `len(x) == 3`, `toHaveCount(4)`. A concurrent test
   added a row. The assertion was never about the count; it was a proxy for
   "my data is there".
3. **Did the page contain something else?** Pagination, default sort, a filter
   that another test changed.
4. **Did the element exist but not first?** `.first()` on an unfiltered locator
   resolves to whatever the DOM happens to put first.

**How to confirm it:** in the log, look at what the test *received*, not at the
assertion. If the expected value appears anywhere in the payload — a different
index, a later page, a second row — the hypothesis is confirmed.

**If confirmed → the test is wrong, not the product.** Rewrite it to be
write-safe (§5), and do it now: a test left assuming position will fail again,
differently, and next time it will cost the full triage a second time.

**If the value is nowhere in the payload → it is a real defect.** Go on.

---

## 2. Second hypothesis: **was it the clock?**

The test waited a fixed number of milliseconds and the machine was busier than
when the number was chosen.

**How to recognise it:** `waitForTimeout` / `time.sleep` anywhere on the path,
*or* a wait for the wrong condition — waiting for an element to be **visible**
when what matters is that it has a **value**.

The canonical example in this tree is W9 (`transfer-same-currency`): the comment
said *"wait for WAC value to populate"* and the line below waited only for the
input to be visible. The blur then fired against an empty field, the product's
"unchanged → do nothing" guard correctly did not fire, and the mode flipped. The
test did not find a defect: **it created the condition it then reported.**

A useful tell: **an instant assertion failure after a long test body is not a
timeout.** `expect(received).toContain(expected)` fails synchronously. If the
test took 10 s and then failed instantly, the 10 s were the body, not the wait —
so do not go looking for a timeout to raise.

**If confirmed → §6.**

---

## 3. Third hypothesis: **did something else move the shared state?**

One backend, one database. Another unit may have emptied, reseeded or
reconfigured what this one depended on.

**How to recognise it:**

- it passes alone and fails in a full run;
- it passes with `--workers 1` and fails above;
- it started failing when a *neighbouring* unit changed.

**How to confirm it:** run the suspected pair in isolation, in order.

```bash
./dev.py test --no-consolidate services all   # 1:1 shape, one process per unit
```

If the red disappears with `--no-consolidate` but not with `--no-shared-server`,
the cause is the shared **pytest session** (a session-scoped fixture, module
state, a monkeypatch that outlived its test). If it disappears with
`--no-shared-server`, the cause is the shared **backend**.

> **Careful — this hypothesis is the easiest to confirm falsely.** "It passes
> alone" is also true of a test that assumes position. Check §1 first; that is
> why it is first.

---

## 4. Fourth hypothesis: **is the loudest symptom the cause?**

When many tests go red at once, the message they share is usually a
*consequence*. Read the **first** failure chronologically, and read what the
runner printed **before** the tests started.

Worked example from this tree. A full `all-backend` produced **13 failures and
116 errors**, all saying `no such table: users`, naming dozens of unrelated
tests. None of them was the cause. Twenty lines above the first test, the setup
had printed:

```
⚠️  Removing existing test database: .../app.db
✅ Test database removed
❌ Create database via Alembic migrations - FAILED
❌ Server is currently running on port 6041
```

The database was deleted, then the migration that should have rebuilt it
correctly refused because a server held the port. Every one of the 116 errors was
a faithful report of a consequence.

**The habit worth keeping: a cascade has one cause. Find where the count of
failures jumps from 0 to many, and look immediately above it.**

---

## 5. Making a read write-safe

The fix is always the same shape: **identify the data by something the test
itself created, and go find it.**

```python
# ✘ assumes position — passes only while nothing else writes
resp = client.get("/api/v1/assets")
asset = resp.json()["items"][0]
assert asset["display_name"] == name

# ✔ verifies — write-safe by construction
name = f"Triage {time.time_ns()}"          # unique, mine, unmistakable
created = client.post("/api/v1/assets", json={"display_name": name, ...}).json()
asset = find_by_id(client, "/api/v1/assets", created["id"])   # walks pages
assert asset["display_name"] == name
```

```ts
// ✘ .first() on an unfiltered locator — whatever the DOM puts first
await page.getByTestId('asset-row').first().click();

// ✔ filtered to the row this test made
await page.getByTestId('asset-row')
          .filter({ hasText: uniqueName })
          .click();
```

Three rules, and they are the same three the instructions state normatively:

1. **Never by position.** No `[0]`, no bare `.first()`, no "page 1".
2. **Never by count**, unless the count *is* the thing under test. `len(x) == 1`
   as a way of saying "my row is there" breaks the moment a neighbour writes.
3. **Never on the clock.** Wait for the condition that actually matters.

Pagination: walk it. If the collection endpoint pages, the helper must follow
`next` until it finds the id, and fail with "not found in N pages" — not assert
on the first page and hope.

---

## 6. When the wait cannot be replaced

Sometimes there is genuinely no condition to wait for. That is **not** a test
problem to be worked around with a cleverer selector: it means a state of the
system is not observable — and it is not observable **to the user either**, who
is looking at the same screen with no way to know whether the operation is done.

So the fix belongs in the product, and it serves both:

- the component makes the state explicit (`idle | pending | done | error`);
- the user sees it as a spinner, a disabled control, a status;
- the test reads the same attribute.

One change, two beneficiaries. **If the right way to surface it is not obvious,
stop and ask** — it is an interface decision, and those are not the test author's
to invent. Bring the list of affected screens, not an abstract question.

---

## 7. Asking for an exclusive resource

A unit that still needs the database to itself after being made write-safe is
telling you something true about the product. It can keep the exclusive, but the
catalogue requires **a written reason** next to it — one line saying what it
mutates that cannot be scoped. Without the line, it does not keep it.

"It's easier this way" is not a reason. "It changes `global_settings`, which is a
single row shared by every user" is.

---

## 8. The verdict

Close every triage with one of these, explicitly:

| verdict | what it means | what follows |
|---|---|---|
| **assumption** | the test assumed position, count or time | rewrite it (§5/§6), in this same session |
| **defect** | the product is wrong | fix it, and keep the test that caught it |
| **shared state** | a neighbour moved what it depended on | scope the neighbour's write, or the read |
| **environment** | setup failed and the tests reported the consequence | fix the setup, make it fail loudly (§4) |
| **slowness** | the product is genuinely too slow under concurrency | its own work item — a red is not the place to fix it |

There is no sixth row. In particular there is no `flaky`.

---

## See also

- `.github/instructions/backend-testing.instructions.md` — the rules, normative
- `.github/instructions/frontend-testing.instructions.md` — same, for Playwright
- `testing-backend` / `testing-frontend` skills — how to write and run tests
- `mkdocs_src/docs/developer/testing/test-walkthrough/runner_architecture.md` —
  why there is one backend and what the isolation classes mean
