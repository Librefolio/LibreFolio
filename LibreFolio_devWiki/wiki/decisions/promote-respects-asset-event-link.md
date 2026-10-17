---
title: "A promote never produces a row linked to an asset event that its type does not admit — refused, never unlinked"
category: decision
status: resolved
date: 2026-10-10
updated: 2026-10-11
tags: [backend, frontend, promote, asset-events, split, suggest, validation, bulk-editor, workstream-p, release-1.2]
related:
  - decisions/transfer-pair-same-asset-opposite-quantity
  - problems/promote-skipped-cost-basis-check
  - decisions/bulk-pairs-new-with-saved
  - entities/transaction-batch-pipeline
  - sources/phase00-promote-pair-checks-2026-10
---

# Decision: a promote respects a row's link to an asset event

## Context

Only DIVIDEND, INTEREST and ADJUSTMENT can be linked to an asset event (rule 9, `eventTypeIncompatible`), and the average
cost treats a row linked to a SPLIT as part of the split. But `apply_promotes` changed the type and linked the rows
without looking at `asset_event_id`: an ADJUSTMENT linked to a SPLIT became a TRANSFER linked to that SPLIT. Red **R42c**
(2026-10-10): a saved ADJUSTMENT −10 and an ADJUSTMENT +10 linked to a SPLIT, with a manual cost → committed. With the
split row in Auto the promote was already refused, but only by chance: Auto writes no cost on a split row, and lot 40's
check asked for one ([[problems/promote-skipped-cost-basis-check]]).

## Options Considered (D2)

1. **Refuse** — recommended by P and chosen by the coordinator (2026-10-10).
2. **Clear `asset_event_id`** — rejected: it would silently drop the link with the SPLIT, and the split's units would
   pass for a transfer.

## Decision

- **Backend** (`7f8233c47`, train 34): `_promoted_state_issues` validates the two rows in their promoted state with the
  same business rules as creates and updates (`validate_transaction_business_rules`). A row linked to an event its new
  type does not admit gives `eventTypeIncompatible` on the `promote` operation, with `ref_id` for saved rows; the
  promote is not applied and the link is untouched.
- **The editor**: `PromoteContext` has optional `eventA` and `eventB`; `findPromoteMatch` gives no match when a row is
  linked and the target type is not event-compatible. The bulk editor (`buildPromoteCtx`) and the transactions page pass
  the rows' `asset_event_id`.
- **The 💡** (found during step 2, decided by the coordinator on 2026-10-11, same lot): `promote_suggest_bulk` ignored
  the link on both sides, so the 💡 and the save reminder offered a linked row that, once imported, nobody could merge —
  a dead end born with D2. `TXPromoteSuggestInput` gained an optional `asset_event_id` (`None` or `0` = not linked,
  additive for old clients); for a linked input the rules whose target type does not admit the link are skipped, and a
  linked candidate is dropped by the same rule. The bulk editor sends each row's link.

## Consequences

- Tests: R42c green; B3.8–B3.10 on `/promote-suggest` (a linked candidate offered next to its unlinked twin; a linked
  input once refused with 422; `null` and `0` as unlinked); PC2b and PC2c in the editor.
- S's PC2 had used a saved ADJUSTMENT linked to a SPLIT as «the only public way» to a saved receiving side without a
  cost. D2 made that promote impossible, so PC2 was rewritten as the UI side of D2 (the banner and the selection offer
  nothing); the cost check on a saved row stays reachable from the API only, covered by
  `test_promote_saved_saved_clearing_cost_basis_is_rejected`.
- The developer docs (`split_promote.md`, the BRIM guide, `transaction-draft.md`) and the user pages on adjustments and
  transfers say that neither row of a pair may be linked to an event.

## Links

- [[decisions/transfer-pair-same-asset-opposite-quantity]] — the same lot's pair rule
- [[entities/transaction-batch-pipeline]] — `apply_promotes` in the stage order
- [[decisions/bulk-pairs-new-with-saved]] — the 💡 and the reminder
- Source: [[sources/phase00-promote-pair-checks-2026-10]]

## Source files

| Role | Path |
|------|------|
| `apply_promotes`, `_promoted_state_issues` | `backend/app/services/transactions/batch_creates.py` |
| `promote_suggest_bulk` | `backend/app/services/transactions/promotion.py` |
| `TXPromoteSuggestInput.asset_event_id` | `backend/app/schemas/transactions/promotion.py` |
| `PromoteContext`, `findPromoteMatch` | `frontend/src/lib/features/transactions/transactionTypeStore.ts` |
| R42c, B3.8–B3.10 | `backend/test_scripts/test_api/test_transactions_batch_split_promote.py` |
| PC2, PC2b, PC2c | `frontend/e2e/transactions/tx-bulk-promote-cost-basis.spec.ts` |
| Developer doc | `mkdocs_src/docs/developer/backend/transactions/split_promote.md` |
