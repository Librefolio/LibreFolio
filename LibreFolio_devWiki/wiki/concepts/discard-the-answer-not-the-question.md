---
title: "Discarding a stale answer is right; discarding the question with it is data loss"
category: concept
date: 2026-08-31
tags: [frontend, async, svelte5, races, ux, method]
related: [concepts/load-only-red-is-a-product-defect, concepts/cancellation-safe-inflight-deduplication]
related_problems: [svelte5-effect-read-write-loop]
---

# Concept: keep the request when you drop the response

## The rule

> Discarding a superseded response is correct. Discarding **the request that
> produced it** is data loss — and it passes unnoticed, because nothing fails.
> Simply, nothing happens.

## Where it came from

Four defects found under load in the same campaign turned out to be one shape:
*an input arrives later than expected, and the code reacts by throwing something
away* — a result, a request, or the user's local edits — treating the late
arrival as if it cancelled the intention that preceded it.

### 1 — the risk catalogue that never arrives

`clientSession.ts` — the **first** identity resolution bumps the session
generation and **returns without running the resetters**; every later transition
runs them. A request started before the app knew who the user was is therefore
discarded on arrival *and* its in-flight slot is never released, because the only
thing that releases it is the skipped resetter.

The catalogue has **one** slot. From there on every call attaches to that
promise and receives `null`. The panel stays at `data-catalog="pending"` for the
life of the page, with nothing on screen. Queries survive because their cache key
contains the user id; the catalogue's does not.

**Fix**: `releaseWhenSettled(promise, release)` — the slot is freed when the
promise settles, not when the generation happens to match. Plus a distinct
`data-catalog="error"`, so *slow* and *failed* stop being the same attribute.

> The first hypothesis — "conditional `finally` blocks in general" — was
> **wrong**, and it fell because the unit test written on it **passed against
> HEAD**. Reproducing the real hole needed `vi.resetModules()` and a re-import of
> *both* modules, because it requires `hasResolvedIdentity === false`: a virgin
> module state. A test that does not fail against HEAD has not described the bug.

### 1b — and once discarded, it never retries

`fetchRiskCatalog` returns `null` when the session generation **or** the cache
generation moves during the request. On an asset page the cache generation moves
for a mundane reason: **opening the page persists the current price**, which
notifies portfolio-mutation listeners, which invalidate risk. Under load that
write lands inside the catalogue fetch window.

**Fix**: up to 3 attempts, re-sampling the generations each round. A discard
means *"this answer describes a world that no longer exists"*, not *"the request
failed"* — so the right reaction is to **ask again**, not to return a `null` the
caller can only report as an error.

### 2 — the comparison that vanishes between click and response

`RiskAnalysisPanel.svelte` — an `$effect` watched a signature (scope, dates,
currency, risk-free rate) and on change zeroed generations, results and loading
flags for **all four** on-demand analyses.

On the asset detail page that signature **settles late**: `dateStart` is rewritten
by `resolveMaxStartFromChartData()` when prices arrive, `displayCurrency` when the
asset arrives. Under load both land *after* the user pressed Compare.

The in-flight result is discarded — correctly, it was computed on superseded
parameters — but **the request goes with it**. `comparisonLoading` returns to
`false`, the whole result block does not render, and the user is left with no
chart, no spinner and no error. Nothing says "press it again".

**Fix**: note which analyses were in flight before zeroing, and **re-launch**
them after.

### 3 — the distribution row that does not exist yet when you save

`DistributionEditor.svelte` — `addEntry` is `async`: the first call loads the
country list. A previous fix had already made the entry **correct**; it did not
make it **timely**. The click handler returns before the row exists, so a Save
pressed immediately after saves **nothing** — and the modal closes as if all was
well.

**Fix**: `addingEntry` with `data-busy` and a disabled button. The window still
exists, but it is now **visible** — to the user and to the test.

### 4 — the data editor that lost pending deletions

`AssetDataEditorSection.svelte` rebuilt `eventRows` from scratch on every new
`events` array reference. The parent assigns a new one on **every**
`loadChartData()`, from ~10 call sites — including the initial page load, which
under load is still in flight while the user is marking deletions.

Rows with `status !== 'original'` do not exist in the server data: they vanished.
`dirtyCount` returned to 0 and Save silently disabled itself.

The invariant was **already written** eight lines below:
*"We don't rebuild eventRows from scratch to preserve the user's pending
edits/deletes."* The line above it was violating it.

**Fix**: do not rebuild while the section is dirty, and leave
`prevEvents`/`prevChartData` unconsumed so the first update after saving enters
normally. **No merge policy** — someone who is writing does not get the document
pulled out of their hands.

## How to spot the shape

- an `$effect` or a guard that **resets state** on a signature change;
- an in-flight slot released by something other than the promise settling;
- a rebuild triggered by an upstream reference change rather than by content;
- a handler that is `async` but whose caller does not await it.

In each case, ask: *if the input arrives late, does the user's intention survive?*

## Source files

| Role | Path |
|------|------|
| Session generation + resetters | `frontend/src/lib/stores/app/clientSession.ts` |
| In-flight slot release | `frontend/src/lib/stores/risk/riskStore.svelte.ts` — `releaseWhenSettled` |
| Signature reset + relaunch | `frontend/src/lib/components/risk/RiskAnalysisPanel.svelte` |
| Async add guarded by `data-busy` | `frontend/src/lib/components/ui/input/DistributionEditor.svelte` |
| Dirty-preserving rebuild | `frontend/src/lib/components/assets/AssetDataEditorSection.svelte` |
| Chart reload call sites | `frontend/src/routes/assets/[id]/+page.svelte` |
