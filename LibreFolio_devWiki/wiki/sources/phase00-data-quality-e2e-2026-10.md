---
title: "Phase 0 / 46 — data-quality E2E on real data (workstream V): items 21–23 of the server checklist"
category: source
source_type: plan
date_ingested: 2026-10-12
original_path: LibreFolio_developer_journal/Release_2/Phase_0/46_dataQualityE2E/plan-phase00DataQualityE2E.prompt.md
tags: [phase0, release2, workstream-v, testing, e2e, data-quality, dashboard, fx, mockfx, cost-basis]
related:
  - decisions/data-quality-proved-on-real-data
  - problems/open-panels-stale-after-fx-sync
  - features/F-054
---

# Source: Phase 0 / 46 — data-quality E2E on real data

## Summary

The plan of workstream V (557 lines, 2026-10-12, still in `Phase_0/`), merged in train 56 (`15bfcf1e8`, `2f0b06346`,
`b44b28f3d`). It turned items 21–23 of the developer's server checklist — missing FX rates and their sync, a missing
cost basis shown as «—», the unrealized breakdown tooltip — from fakes into end-to-end tests on real data, through
the API and a disposable account per test. It proves the real «Sync rates» offline with the MOCKFX provider, reaches
a missing cost three ways (the developer's D1, «(c) Entrambe»), and found and fixed one defect on the way: open
panels did not refresh after the sync (D2). Seven items were left for after release 1.2 (V-1…V-7).

## Key takeaways

- **The method**: [[decisions/data-quality-proved-on-real-data]] — four tests (B1 backend; E1–E3 real data; E4
  legacy rows), MOCKFX for an offline but real sync, reserved currencies per project, and a helper that writes legacy
  rows into the lane's test database only.
- **The defect**: [[problems/open-panels-stale-after-fx-sync]] — `refreshVersion` was not sent after the sync; red
  first, then the one-line fix.
- **Verified before writing**: the kickoff's claims were checked one by one (§1.1): one test path was wrong, the seed
  cannot produce `MISSING_COST_BASIS`, and the gaps were real.
- **Two testability attributes**: `data-column-id` on DataTable cells and the `kpi-unrealized-delta` test id.
- **A red that was not V's**, triaged with the test-triage skill: `dashboard-cache.spec.ts` failed next to
  `dashboard-broker-filter-label`, which creates and deletes a broker of the shared `TEST_USER` (V-7).

## Wiki pages created or updated

- Created: [[decisions/data-quality-proved-on-real-data]], [[problems/open-panels-stale-after-fx-sync]].
- Updated: [[features/F-054]] (status history).

## Source files

| Role | Path |
|------|------|
| The plan | `LibreFolio_developer_journal/Release_2/Phase_0/46_dataQualityE2E/plan-phase00DataQualityE2E.prompt.md` |
| Backlog section V (V-1 … V-7) | `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` |
| The real-data spec | `frontend/e2e/portfolio/data-quality-real.spec.ts` |
| The legacy-rows spec and its helper | `frontend/e2e/portfolio/data-quality-legacy.spec.ts`, `backend/test_scripts/test_db/legacy_cost_rows.py` |
| The fix | `frontend/src/routes/(app)/dashboard/+page.svelte` |
