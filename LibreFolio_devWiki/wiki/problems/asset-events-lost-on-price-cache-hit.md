---
title: "With the prices already cached and no signal active, the asset page returned early and the events never arrived: «No data» for an asset with five events"
category: problem
status: resolved
date: 2026-08-06
tags: [frontend, assets, events, cache, chart, early-return, silent-error]
related:
  - features/F-033
  - sources/phase00-clean-audit-2026-08
---

# Problem: events that vanished on a cache hit

## Symptom

On an asset's page, the events editor and the chart showed «No data» for an asset that had five events — no error, no
log. Found while making the full test suite pass end to end, the last step of the clean audit of August 2026: «cache
dei prezzi + nessun segnale attivo ⇒ gli eventi svanivano in silenzio» (`17_stabilizzazione_suite_completa.md`).

## Root Cause

`loadChartData()` returned early when the price store already covered the requested range and no signal was active.
But events travel only in the same response as the prices (`include_events: true`): skipping the request skipped the
events too. The early return came with the price cache, added in July (`5b9dddb45`).

## Solution

`b45f5afbb` («fix(tests): make the full suite runnable end-to-end and fix…»): no early return; on a cache hit the page
falls through to an events-only request (`include_price: false`). Loading state, chart data and the error path are all
guarded by the same cache flag, so the fall-through changes nothing else.

## Prevention

When a cache short-circuits a request, check what else that request carried: a response that bundles two kinds of
data cannot be skipped for one of them.

## Source files

| Role | Path |
|------|------|
| `loadChartData()` | `frontend/src/routes/(app)/assets/[id]/+page.svelte` |
| Journal | `LibreFolio_developer_journal/Release_2/phases/05_cleanAudit/17_stabilizzazione_suite_completa.md` |
