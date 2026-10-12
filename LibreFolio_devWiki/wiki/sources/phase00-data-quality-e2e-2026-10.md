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
  - problems/e2e-writes-leaked-into-shared-state
  - decisions/e2e-gaps-of-1-2-before-release
  - problems/bcrypt-blocks-the-event-loop
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

## Batch 2 and work 3 (trains 58 and 64, added 2026-10-12)

The plan grew after this page was written (registered now at `262515898`):

- **Batch 2, §11 (train 58)** — the coordinator's mandate «nello spirito della decisione D2»: V-1, «Sync prices» did not
  refresh open panels, red first then `refreshVersion += 1` (`a0722f755`,
  [[problems/open-panels-stale-after-fx-sync]]); V-7, `dashboard-broker-filter-label` moved to a disposable account
  owning two brokers (`4e710a1f9`); V-5 and V-6, a comment and the developer doc's test list (`6f5a3bcff`). docs-writer
  found V-9 and V-10.
- **Work 3, step 1, §12.1–§12.2 (train 58)** — V-9, two outdated sentences of the banner doc (`973ca3961`); V-10, two
  latent defects of `data-quality-banners.spec.ts`, which now pins the header counts on a heading the test decides
  (`8994100b4`). Three more findings went to the backlog: V-11 (`TRANSACTION_IMPLIED` can claim no market price for
  over two weeks on an asset quoted yesterday), V-12, V-13; and V-14 (probes still tied to the seed).
- **Work 3, step 2, §12.3 and §12.5 (train 64)** — the audit of the E2E suite's writes and checkpoint 2a, cures A1–A3:
  reserved MOCKFX pairs, disposable accounts, the scheduler's keys read and restored —
  [[problems/e2e-writes-leaked-into-shared-state]]. The gate's six reds outside the batch were triaged: V-19 (a Spanish
  label past the toolbar, [[concepts/responsive-4mode-layout]]), V-20 (3 s waits under load), V-17 (the runner);
  test-author also found V-16, [[problems/bcrypt-blocks-the-event-loop]].
- **Work 3, step 3, §12.4** — eight E2E gaps of 1.2, and the developer's «Tutte e 7 nella 1.2» —
  [[decisions/e2e-gaps-of-1-2-before-release]] (planned).
- **Open in section V** after train 64: V-2, V-3, V-4, V-8 (the Risk panel with a vanished broker: a 403 and no
  re-read; needs a decision), V-11…V-20; checkpoint 2b (A4–A7) to come.

## Step 2b (train 72, added 2026-10-12)

The E2E specs that wrote into shared state now clean up, each with its damage proved first: A4 to A7, V-20 and the
notes of the Playwright configuration — [[problems/e2e-writes-leaked-into-shared-state]]. The cleanup unmasked WB5,
which passed only on other tests' leftovers — [[problems/test-passed-only-on-leftovers-of-other-tests]]. The
backlog gained V-21 (probes, forbidden selectors and undeleted uploads left in the specs), V-22 («+ New event» can
change an existing event while saying it created one — a product question) and V-23 (the bulk editor hides the
read-only broker and puts the access error on the wrong row); V-20 is closed.

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
