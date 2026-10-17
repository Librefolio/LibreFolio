---
title: "WB5 passed only on other tests' leftovers: it cloned the first pair it found, a seed pair the test user may only view, and the cleanup of step 2b unmasked it"
category: problem
status: resolved
date: 2026-10-12
tags: [testing, e2e, playwright, isolation, test-data, wac, bulk-editor, broker-access, workstream-v, release-1.2]
related:
  - concepts/test-isolation-classes
  - problems/e2e-writes-leaked-into-shared-state
  - sources/phase00-data-quality-e2e-2026-10
---

# Problem: a test that leaned on another test's mess

## Symptom

In the gates of workstream V's step 2b (2026-10-12), `tx-wac-bulk.spec.ts` «WB5 — Clone paired from DB, WAC auto cell
appears (inline validate)» went red: after the clone, the WAC «auto» cell stayed `empty` for 20 s instead of becoming
`ready`. It failed alone at one worker too, so it was not load.

## Root Cause

- **It took a pair by position.** WB5 cloned the first suitable pair in the list: the seed's MSFT pair from Interactive
  Brokers to DEGIRO, built for the asymmetric-access cases — on DEGIRO `e2e_test_user` is only a VIEWER.
- **The product was right.** Validate answered `accessDenied` («EDITOR required for broker 2») with no WAC result,
  and `compute_wac_and_fx_issues` (`transaction_batch_stages.py`) proposes no cost for a batch with errors: `empty` is
  the correct state, and the banner says why.
- **Why it had passed**: since `9a254f812` (2026-08-14) WB5 has required `ready`, and from then on it passed only when
  the first pair was one left by another test — the IB→Directa pair that WB4, before it in the same file, commits and
  never deletes, or the leftovers of `tx-commit-all-types`. Alone it always failed; at four workers it started beside
  WB4 and failed; in sequence it passed.
- **Step 2b removed the leftovers** — A4 now deletes the commits of `tx-commit-all-types` — and WB5 lost its
  accidental data. Plan 46: «La pulizia della 2b l'ha smascherato» ("2b's cleanup unmasked it").

## Solution

`1ea16aace` («test(e2e): own the WB5 pair, clean up WB4», train 72):

- **WB5 owns its data**: two brokers and an EUR asset created through the API, two ADJUSTMENT +10 at 100 and 200 EUR,
  a linked TRANSFER −4/+4 with a manual cost of 175 on the receiving side; it clones that pair by id and asserts
  `ready` and the expected cost (150 EUR per unit); `cleanupOwned` removes everything in `finally`.
- **WB4 cleans up**: it records the ids it commits and deletes them in `finally`.

11 of 11 at one and at four workers; `front-transaction all` 327 of 327 on the re-run.

## Prevention

- A test that writes owns what it touches, as the isolation classes require ([[concepts/test-isolation-classes]]): it
  may read the seed, but it must not pick «the first pair» and assume what it is or who may edit it.
- A test that passes only in a given order, or only beside a given neighbour, is reading someone else's state:
  removing leftovers is a good way to find such tests, and they should be fixed, not loosened.
- The product observations from the same reading — the read-only broker hidden in the bulk editor, the access error
  on the wrong row — are backlog V-23.

## Source files

| Role | Path |
|------|------|
| The spec (WB4, WB5, `cleanupOwned`) | `frontend/e2e/transactions/tx-wac-bulk.spec.ts` |
| WAC and FX issues of a batch | `backend/app/services/transactions/batch_costs.py` |
| Plan 46 (step 2b) | `LibreFolio_developer_journal/Release_2/Phase_0/46_dataQualityE2E/plan-phase00DataQualityE2E.prompt.md` |
| Backlog (V-23) | `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` |
