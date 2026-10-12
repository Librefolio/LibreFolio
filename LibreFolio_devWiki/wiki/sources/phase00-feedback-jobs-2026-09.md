---
title: "Phase 0 / 09 — the feedback jobs: the backlog of the September round, split into 16 sprints, and where each job went"
category: source
source_type: plan
date_ingested: 2026-10-12
original_path: LibreFolio_developer_journal/Release_2/Phase_0/09_feedbackJobs/
tags: [phase0, release2, feedback, backlog, sprints, workstreams, coordination, release-1.2]
related:
  - sources/phase00-feedback-import-urgent-2026-09
  - sources/phase00-performance-charts-2026-09
  - sources/phase00-asset-data-operations-2026-09
  - sources/phase00-brim-targeted-2026-09
---

# Source: Phase 0 / 09 — the feedback jobs

## Summary

Folder 09 was opened on 2026-09-07 as the backlog of the next development round: a review of `TODO_FUTURI.md` sorted
with the developer, plus the eight P4 tasks inherited from audit 08. Its README: «Backlog del prossimo round di
sviluppo. Ogni file è un'area; i task dentro hanno contesto, dettagli implementativi e rimandi al codice/ai piani.»
`06_piano_sprint.md` split it into 16 sprints (SP01–SP16), run as parallel workstreams B and D–L; files 08 and 09 add
the production visual review of 22/09 (R1–R21) and the static-analysis findings of the same day. The code check of
2026-10-09 (base `3cceb4f90`) found almost everything delivered. This page is step F0 of its ingest.

| Area (file) | Where it went | Wiki source | Status, with evidence |
|-------------|---------------|-------------|-----------------------|
| 00, structural backlog P4 | P4-1/P4-4 → asset pricing refactor (K); P4-2 → transaction batch refactor (L); P4-5 → contracts and runes | [[sources/phase00-asset-pricing-refactor-2026-09]], [[sources/phase00-transaction-batch-refactor-2026-09]], [[sources/phase00-feedback-contracts-runes-2026-09]] | partly: P4-11 closed in `804bc9903`; P4-7, P4-9, P4-10 open |
| 01, dashboard UX | U1/U4/U5/U7/U9 → urgent import fixes (E); U3 → yield on cost (H); U2 → privacy (J); U8 → onboarding (J) | [[sources/phase00-feedback-import-urgent-2026-09]], [[sources/phase00-yield-on-cost-2026-09]], [[sources/phase00-privacy-global-2026-09]], [[sources/phase00-onboarding-2026-09]] | delivered (U2: `b66e93003`) |
| 02, advanced charts | G1a–G1c, G3 → performance charts (I) | [[sources/phase00-performance-charts-2026-09]] | delivered (`2c382824d`) |
| 03, asset data | A1/A2 → asset data operations (F) | [[sources/phase00-asset-data-operations-2026-09]] | delivered (`e50d66408`) |
| 04, BRIM import | P4-3/B1 → BRIM targeted (G) | [[sources/phase00-brim-targeted-2026-09]] | delivered (SP09, `ebba209c5`) |
| 05, PAC tool | the planner → PAC allocator (D) | [[sources/phase00-pac-implementation-2026-10]] | partly: planner delivered (`b82e59ffa`); SP14 Rebalancer not built ([[features/F-108]]) |
| 07, critical import feedback | E1–E9 → urgent import fixes | [[sources/phase00-feedback-import-urgent-2026-09]] | delivered (`ef722b552`) |
| 08, visual review 22/09 | spread across the lots | — | partly: all closed except R2 |
| 09, static analysis 22/09 | spread across the lots | — | partly: defects closed; the §2.4 debt open |

## Still open (the README's check of 2026-10-09; paths as of today)

- **P4-7**: the frontend's price-store registry (`stores/assetPriceStoreRegistry.ts`) is a `Map` with no bound and
  no eviction.
- **P4-9**: seven re-pinned mirror tests in `chartCoreHelpers.test.ts` still to convert.
- **P4-10**: six Risk sites outside the masking channel, to re-check after privacy round 2
  (`moneyRenderSites.test.ts`).
- **R2**: a stale `VERSION` file is read before `git describe` (`utils/runtime/version.py` since BU1), and the Docker
  build leaves it at the root.
- **§2.4**: the guard of the fake catalogue, a declared debt.
- **SP14**: the Rebalancer, D's next work ([[features/F-108]]).
- **SP15**: `SensitiveValue`, suspended since 21/09.

## F1 — the structural backlog and the static analysis (step F1)

Checked at `7ff48ac9b`: P4-1 (`asset_source.py` split into `services/asset_sources/`), P4-2 (`execute_batch` in
stages), P4-3, P4-4, P4-5 and P4-6 (`514582a47`), P4-11 (`804bc9903`) are delivered; P4-7, P4-9 and P4-10 are open
(above). Of the static analysis, §1.1, §1.4, §1.6, §2.1–§2.3, §2.5 and §2.6 are closed, §1.2, §1.3 and §1.5 were
withdrawn as non-defects, §1.7 kept its keys by the developer's decision, §2.7 keeps the history as written, and §2.4
is open. Two solved defects worth keeping: [[problems/privacy-gate-blind-to-formatter-consumers]] and
[[problems/missing-event-detail-read-as-consent]].

## Source files

| Role | Path |
|------|------|
| README (status and open items) | `LibreFolio_developer_journal/Release_2/Phase_0/09_feedbackJobs/README.md` |
| Sprint plan | `LibreFolio_developer_journal/Release_2/Phase_0/09_feedbackJobs/06_piano_sprint.md` |
| P4-7 site | `frontend/src/lib/stores/assetPriceStoreRegistry.ts` |
| R2 site | `backend/app/utils/runtime/version.py` |
