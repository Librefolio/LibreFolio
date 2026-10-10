---
title: "Phase 0 / 33 — E2E import test infrastructure (train 10)"
category: source
source_type: plan
date_ingested: 2026-10-09
original_path: LibreFolio_developer_journal/Release_2/phases/33_e2eImportInfra/plan-phase00E2eImportInfra.prompt.md
tags: [phase0, release2, testing, e2e, playwright, brim, import, flaky, fixtures]
related:
  - problems/reused-ids-after-delete
  - problems/account-deletion-orphaned-brokers
  - problems/compactcashcell-decimal-separator-feedback-loop
  - concepts/e2e-data-testid-rule
  - concepts/transaction-hygiene-fixture
  - sources/phase00-account-and-id-reuse-2026-10
---

# Source: Phase 0 / 33 — E2E import infrastructure

## Summary

One plan (~290 lines), shipped in train 10 (commits `860c934ac`, `abfcdf2be`, `ffdcacc2f`, `cc15441e6`) and archived on
2026-10-09. It made the import E2E specs deterministic — and, checking whether their leftovers could happen in
production, found two real defects that plan 34 then fixed: [[problems/account-deletion-orphaned-brokers]] (A) and
[[problems/reused-ids-after-delete]] (B).

## Key takeaways

- **Leftover report files**: a broker showed files from earlier runs because `populate --force` deleted the database
  but not `broker_reports/`, and broker ids were reused. Fix: `reset_broker_reports(data_dir, db_path)` empties
  `uploaded/`, `parsed/` and `failed/` — only when the database lives under that data directory — and leaves `.locks`
  and `custom-uploads` alone (`backend/test_scripts/test_db/populate_mock_data.py`; test `test_populate_reset.py`).
  The runner's `db create` already reset the file store: a precedent nobody had noticed.
- **Timing flakes**: helpers used `isVisible({timeout})`, which does not wait (the same trap as in
  [[problems/compactcashcell-decimal-separator-feedback-loop]]), and picked files with `.first()`. Now one shared
  fixture drives the wizard by reading the stepper (`[aria-current="step"][data-step-id]`), confirms warnings only when
  the parse response says there are some, and finds files by name, page by page
  (`frontend/e2e/fixtures/import-wizard.ts`: `uploadOwnedReport`, `deleteOwnedReports`, `selectBrokerFile`,
  `parseSelectedFile`, `continueToStep`, `continueToReview`; `fixtures/paging.ts`).
- Each spec owns and deletes what it creates (the Crédit Agricole contract spec now removes its broker and file in
  `afterEach`).
- A `core-unit` red: `optionFilter.test.ts` now reads only the body of the class decorated with `@register_provider`.

## Residuals (backlog 38)

L11 — remaining quality debt of the import specs (fixed sleeps, a serial `tx-brim-import`, a few CSS-based lookups).
L12 (from plan 34) — E2E users are created as administrators.

## Wiki pages updated

- None of its own: its two production findings are filed under plan 34's pages.

## Source files

| Role | Path |
|------|------|
| Plan | `LibreFolio_developer_journal/Release_2/phases/33_e2eImportInfra/plan-phase00E2eImportInfra.prompt.md` |
| Wizard fixture | `frontend/e2e/fixtures/import-wizard.ts` |
| Paging helper | `frontend/e2e/fixtures/paging.ts` |
| Report-folder reset | `backend/test_scripts/test_db/populate_mock_data.py` |
| Reset test | `backend/test_scripts/test_db/test_populate_reset.py` |
| Import specs | `frontend/e2e/transactions/tx-brim-import.spec.ts` |
| Crédit Agricole contract spec | `frontend/e2e/transactions/tx-import-ca-contract.spec.ts` |
| File selection spec | `frontend/e2e/transactions/tx-import-file-selection.spec.ts` |
