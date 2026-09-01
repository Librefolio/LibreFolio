---
title: "Phases 0-1-2 and the sync / pure-logic lanes"
category: source
source_type: plan
date_ingested: 2026-08-31
original_path: "LibreFolio_developer_journal/Release_2/Phase_0/07_coverageAndConsolidationCampaign/plan-storico-fase012.md, plan-storico-corsie-sync-e-logica.md"
tags: [testing, coverage, frontend, sync, dates, metrics]
related:
  - concepts/coverage-rate-vs-volume
  - concepts/load-only-red-is-a-product-defect
  - problems/utc-today-vs-user-calendar
  - problems/svelte-template-branches-not-instrumented
---

# Source: phases 0-1-2, sync lane, pure-logic lane

## Summary

The opening lanes of the coverage campaign, plus the two lanes that targeted the
sync subsystem and pure logic modules. Their lasting output is not the coverage
delta but three measurement findings and one class of product defect.

## Key Takeaways

- **The night run found what the day hid.** A run finishing after midnight went
  red on `tx-clone`, and the audit that followed found
  `new Date().toISOString().slice(0,10)` in **18 places** — three of them product
  defects. Full classification in [[problems/utc-today-vs-user-calendar]].
- **"Why does the number barely move"** was answered here with arithmetic rather
  than intuition: a point costs ~321-362 lines, and the denominator grows as
  files enter the map. See [[concepts/coverage-rate-vs-volume]].
- **Monocart publishes five metrics** and titles itself with the most generous
  (Bytes, 83,17 %). Branches, at 53,75 %, is the only one that answers *"was this
  behaviour verified?"*.
- **Svelte template branches are not instrumented at all.** Proved on a minimal
  case with an empty `branchMap` —
  [[problems/svelte-template-branches-not-instrumented]]. This is why extracting
  logic into `.ts` is a *measurement* requirement, not a style preference.
- **`sortFn` was never read.** A prop threaded through the table components and
  consumed by nobody: dead configuration that looked like a feature.
- **Two lists walked at different speeds.** The sync lane found paths that
  iterate the same collection with different cursors, the same shape that later
  produced the off-by-one in bulk validation
  ([[concepts/load-only-red-is-a-product-defect]]).

## Source files

| Role | Path |
|------|------|
| Sync service | `backend/app/services/sync_service.py` |
| Sync UI | `frontend/src/lib/components/sync/` |
| Table components (`sortFn`) | `frontend/src/lib/components/table/` |
| Date sentinels and range store | `frontend/src/lib/utils/dateOnly.ts`, `frontend/src/lib/stores/dateRangeStore.svelte.ts` |
| Spec date helpers | `frontend/e2e/fixtures/dates.ts` |
| Original plans | `LibreFolio_developer_journal/Release_2/Phase_0/07_coverageAndConsolidationCampaign/plan-storico-fase012.md`, `plan-storico-corsie-sync-e-logica.md` |
