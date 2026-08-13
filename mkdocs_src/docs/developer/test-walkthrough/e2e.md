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

!!! warning "A signal can exist and still be lying"

    `ImageEditModal` sets `data-cropper-ready` as soon as the cropper can paint — but the modal
    keeps **discarding change events for another ~500 ms** while it runs its own reset pass. Edits
    made in that window disappear, for the spec and for the user, who can then close the modal and
    lose them without a warning. The spec had answered with `waitForTimeout(1500)`. The fix was to
    publish the state that actually decides (`data-edit-ready`), not to sleep longer.

    When you write *"extra settle time"*, *"let it load"*, *"wait for X to finish"* in a comment,
    you have just named a state the product does not expose.

## 🔍 When a spec fails

Use the **`test-triage`** skill. Its first hypothesis is *"was it the shape of the response?"* —
the data was there but elsewhere, the page held something else, the count differed. **`flaky` is not
a verdict.**
