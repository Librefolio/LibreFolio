---
title: "A TRANSFER pair moves one asset in exactly opposite quantities — checked by the backend, the editor and the selection bar"
category: decision
status: resolved
date: 2026-10-10
updated: 2026-10-11
tags: [backend, frontend, transfer, promote, pairs, validation, decimal, bulk-editor, workstream-p, release-1.2]
related:
  - decisions/promote-respects-asset-event-link
  - decisions/bulk-pairs-new-with-saved
  - decisions/pair-description-tags-validation
  - decisions/cash-transfer-split-promote
  - sources/phase00-promote-pair-checks-2026-10
---

# Decision: a TRANSFER pair is one asset, in exactly opposite quantities

## Context

The transaction-type metadata declared a TRANSFER pair's constraints — same asset, different brokers, opposite
quantity — but only the promote of saved rows used them (`_check_promote_constraints`). `_validate_linked_pair`
checked only the type and, for TRANSFER and CASH_TRANSFER, the brokers. When the bulk editor promoted two **new** rows it
did so locally — both rows TRANSFER, one shared `link_uuid` — and the backend accepted the created pair as it came.
Red tests from the test author, from workstream S's findings (2026-10-10):

- **R42a**: −3 on broker A, +5 on broker B → committed. Two units were born from nothing;
- **R42b**: asset X out of A, asset Y into B → committed;
- **G42** (green): a promote of a saved row with a new one already refused −3/+5 (`noPromoteRule`).

The editor proposed such pairs: `findPromoteMatch` compared only the signs (`qA > 0 && qB < 0`).

## Decision

The coordinator's decision D1 = (a), on P's recommendation (2026-10-10); the developer had already said that a defect
confirmed by a red test enters 1.2:

- **Backend** (`7f8233c47`, train 34): for a TRANSFER pair, `_validate_linked_pair` refuses different assets
  (`pairAssetMismatch`) and quantities that are not exactly opposite in `Decimal` (`pairQuantityMismatch`, with `qtyA` and
  `qtyB`). Both keys exist in the four catalogues.
- **The editor's rule**: in `findPromoteMatch`, «opposite» means `qA !== 0 && qA === -qB`, so −3/+5 is no longer
  proposed, locally or with saved rows.
- **Exact decimals where it matters**: the banner pairs securities with `assetQuantitiesCancel` and cash with
  `cashAmountsCancel`, both in exact decimal arithmetic since this lot (`cashAmountsCancel` lost its `Number` tolerance
  of 1e-9). The selection bar followed on 2026-10-11 (C-46, `bdec709d2`, train 37): `-123456789012.123456` and
  `+123456789012.123457` are the same double but not the same decimal, and the bar offered them.
- **Scope**: only TRANSFER. The other declared constraints — CASH_TRANSFER (opposite amount, same currency),
  FX_CONVERSION (different currencies, same broker) — went to backlog C-42: forms and imports already respect them, so
  only API clients could break them.

## Consequences

- Tests: R42a, R42b green; `transactionTypeStore.test.ts` (F1–F4 red first, then green; registered in `tx-unit`); the
  «exact at large magnitudes» block of `promoteHelpers.test.ts`; PC5 in `tx-bulk-promote-cost-basis.spec.ts` for the bar.
- Open, with C-42: an API update that changes the quantity of only one leg of a saved TRANSFER is not checked —
  `validate_updated_pairs` looks only at description and tags ([[decisions/pair-description-tags-validation]]).
- Reported, not changed: the grid's quantity cell shows `parseFloat(qty)`, so the two sides of PC5's pair look equal and
  the user cannot see why they do not merge.

## Links

- [[decisions/promote-respects-asset-event-link]] — the same lot's other rule
- [[decisions/bulk-pairs-new-with-saved]] — the banner and «Merge all» these checks guard
- [[decisions/cash-transfer-split-promote]] — promotes through the batch pipeline
- [[decisions/orphan-transfer-becomes-an-adjustment]] — the other side of the rule: a TRANSFER whose pair was deleted
  with its broker (V-3, decided 13/10, after 1.2)
- Source: [[sources/phase00-promote-pair-checks-2026-10]]

## Source files

| Role | Path |
|------|------|
| `_validate_linked_pair` | `backend/app/services/transactions/validation.py` |
| `findPromoteMatch` | `frontend/src/lib/features/transactions/transactionTypeStore.ts` |
| `cashAmountsCancel` | `frontend/src/lib/features/transactions/bulk/promoteHelpers.ts` |
| `assetQuantitiesCancel` | `frontend/src/lib/features/transactions/bulk/promoteSuggest.ts` |
| The selection bar (`selectedForPromote`; its button in `frontend/src/lib/features/transactions/bulk/TxBulkToolbar.svelte`) | `frontend/src/lib/features/transactions/bulk/TransactionBulkModal.svelte` |
| R42a, R42b, G42 | `backend/test_scripts/test_api/test_transactions_batch_split_promote.py` |
| The editor's rule, tested | `frontend/src/lib/features/transactions/transactionTypeStore.test.ts` |
| PC5 | `frontend/e2e/transactions/tx-bulk-promote-cost-basis.spec.ts` |
| Plan 42 | `LibreFolio_developer_journal/Release_2/Phase_0/42_promotePairChecks/plan-phase00PromotePairChecks.prompt.md` |
