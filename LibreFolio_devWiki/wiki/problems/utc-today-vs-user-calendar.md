---
title: "`toISOString().slice(0,10)` is not today — 18 sites, 3 product defects"
category: problem
status: resolved
date: 2026-08-29
tags: [frontend, dates, timezone, testing, product-defect]
related: [decisions/scheduler-converts-at-decision, concepts/load-only-red-is-a-product-defect]
---

# Problem: the UTC calendar day is not the user's calendar day

## How it was found

A full run finished after midnight and `tx-clone.spec.ts` went red. For 22 hours
a day the UTC date and the Europe/Rome date agree; the suite almost always runs
inside those 22 hours.

> The run that found it is the run nobody schedules.

## Root cause

`new Date().toISOString().slice(0, 10)` returns the **UTC** calendar day. East of
Greenwich, between local midnight and UTC midnight, that is *yesterday*.

An audit found the pattern in **18 places**.

## The classification, which is the useful part

| verdict | count | examples |
|---|---|---|
| **product defect** | 3 | `dateRangeStore.defaultRange()`, `resolveDateSentinel('max')`, `DataEditor.handleAddRow()` |
| **test defect** | 1 | `tx-clone.spec.ts` |
| **correct as written** | 14 | internal UTC arithmetic; dates that arrive from the backend already in UTC |

The three product defects are all *"what does today mean to the person looking at
the screen"*:

- `defaultRange()` — the dashboard opens on a range that **ends yesterday**, so
  a transaction entered this evening is not in the default view.
- `resolveDateSentinel('max')` — a `max` sentinel resolves to yesterday, so a
  filter that should include today excludes it.
- `DataEditor.handleAddRow()` — a new row is pre-filled with **yesterday's**
  date, and the user has to notice and correct it.

The fourteen correct ones matter too. A blanket replacement would have broken
them: UTC arithmetic on values that are already UTC is right, and rewriting it to
local time introduces the mirror-image bug.

> The audit's product is not the fix list. It is the **classification** — three
> categories with a reason each. A patch applied to all 18 would have fixed 3 and
> broken 14.

## Fix

`frontend/e2e/fixtures/dates.ts` exposes `localIso`, `todayIso`, `daysAgoIso`,
used by the specs. It is a **fixture** file, not `$lib`, for a mechanical reason:
Playwright specs run outside the SvelteKit build and do not resolve the `$lib`
alias.

The product sites were corrected to the local calendar; the internal-arithmetic
sites were left alone with a note.

The guard test **freezes the clock** rather than asserting a computed date —
otherwise it would be green for 22 hours a day, which is the failure mode it
exists to prevent.

## Relationship to the scheduler decision

This is the same family as [[decisions/scheduler-converts-at-decision]]: the
question is always *at which point does an instant become a calendar day, and in
whose calendar*. The scheduler answered it for stored times; this answers it for
`now()`.

## Source files

| Role | Path |
|------|------|
| Spec date helpers | `frontend/e2e/fixtures/dates.ts` — `localIso` (L20), `todayIso` (L25), `daysAgoIso` (L30) |
| Dashboard default range | `frontend/src/lib/stores/dateRangeStore.svelte.ts` — `defaultRange()` (L20) |
| Sentinel resolution | `frontend/src/lib/stores/dateRangeStore.svelte.ts` — `resolveDateSentinel()` (L144) |
| New-row prefill | `frontend/src/lib/components/ui/data-editor/DataEditor.svelte` — `handleAddRow()` (L456) |
| Spec that first went red | `frontend/e2e/transactions/tx-clone.spec.ts` |

> **Path note (2026-09-01)**: the substance of this page held up; the addresses did
> not. Three rows were wrong: the store had moved to `.svelte.ts`, `DataEditor.svelte`
> had moved to `ui/data-editor/`, and `resolveDateSentinel` was attributed to a
> `dateSentinels.ts` that does not exist — the function lives in
> `dateRangeStore.svelte.ts` next to `defaultRange()`, which is itself the point:
> **two of the three product defects are twelve lines apart in the same file.**
> All five rows re-verified against the tree, symbol by symbol.
