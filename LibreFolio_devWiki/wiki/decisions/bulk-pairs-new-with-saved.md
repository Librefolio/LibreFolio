---
title: "Bulk editor: pair new rows with saved ones, remind before saving, merge all — only pairs that cancel exactly"
category: decision
status: resolved
date: 2026-10-10
tags: [frontend, bulk-editor, promote, suggest, cash-transfer, transfer, import, decimal, workstream-s, release-1.2]
related:
  - decisions/cash-transfer-split-promote
  - decisions/pair-description-tags-validation
  - decisions/scalable-two-accounts-two-plugins
  - problems/merged-transfer-not-seen-as-duplicate
  - features/F-048
  - sources/phase00-brim-scalable-2026-10
---

# Decision: the bulk editor pairs new rows with saved ones

## Context

The bulk editor suggested pairs — the 💡 on a row and the banner — for two new rows or two saved ones, never a new row
with a saved one, although the backend and the mixed branch of `executePromote` supported it. Whoever imported
Scalable's overnight account a month after the broker would never have seen the two halves of each internal transfer
meet ([[decisions/scalable-two-accounts-two-plugins]]).

## Decision

Plan 37, §8, and its steps 11, 12b and 12f:

- **New + saved** (`94271713b`, 2026-10-09). `promote-suggest` also receives the new, unlinked rows, with negative ids
  (`newRowSuggestId`), when they have a type, a broker, a date and a non-zero amount or quantity (`isSuggestable`);
  without an amount the backend would skip the opposite-amounts check and return every deposit in the window. The 💡
  and the banner offer the mixed pairs (`mixedPromotePairs`, `importableSuggestions` in `promoteSuggest.ts`), merged
  through the existing mixed branch.
- **A reminder at save**, when some suggestions were never looked at (the 💡 never opened, the banner never touched),
  with «Show the suggestions» and «Save anyway»; and **«Merge all»** in the banner, beyond one pair, with one choice for
  every pair (`PromoteAllModal`: all left, all right, combine). It counts and merges only pairs that share no row
  (`2046b7419`, 2026-10-10).
- **Securities pairs only when they cancel** (the coordinator's decision, `1a4fe32a4`, 2026-10-10): a TRANSFER pair is
  offered only for the same asset with opposite, non-zero quantities equal in **exact decimal arithmetic**
  (`assetQuantitiesCancel`, on `exactDecimalSign` and `exactDecimalEqual`), as the backend checks it. A first version
  with a relative tolerance of 1e-9 let through pairs the backend would refuse.
- An answer of `promote-suggest` overtaken by a newer question is discarded (`suggestAskedKey`), so a half just merged
  is not offered again.

## Consequences

- Fixed on the way: in the new + new branch the sign was lost when the type became `CASH_TRANSFER` or `FX_CONVERSION`
  (the editor shows absolute amounts and leaves the sign to the type), and `collapseIntoPaired` picked the «from» side
  at random. The sign now goes into the amount before the type changes.
- Reported by S to workstream P on 2026-10-10 and closed by P's lot 42 (`7f8233c47`, train 34): exact cash
  cancellation in `cashAmountsCancel`, one asset and exactly opposite quantities for a TRANSFER pair
  (`pairAssetMismatch`, `pairQuantityMismatch`), and no merge of a row linked to an asset event
  (`eventTypeIncompatible`).
- A spec that saves the bulk editor on the shared E2E user with an unseen suggestion now stops on the reminder.
- The pairs it offers follow lot 42's rules: one asset in exactly opposite quantities ([[decisions/transfer-pair-same-asset-opposite-quantity]]),
  and no row linked to an asset event its new type does not admit ([[decisions/promote-respects-asset-event-link]]).
- C-47 (2026-10-11, `bdec709d2`): the *Max Δ days* slider reached 0 while `/promote-suggest` wanted at least 1, and
  moving it did not search again. The endpoint accepts 0 (the same day only), and the window is part of the 💡's search
  key.
- The cost check on promotes is lot 40's ([[problems/promote-skipped-cost-basis-check]]); S's spec
  `tx-bulk-promote-cost-basis.spec.ts` verifies that its refusal lands on the right row of the editor.

## Links

- [[decisions/cash-transfer-split-promote]] — promotes through the batch pipeline
- [[decisions/pair-description-tags-validation]] — the two sides of a pair share description and tags
- [[problems/merged-transfer-not-seen-as-duplicate]] — the same pairs, exported again
- [[features/F-048]] — the transaction modals

## Source files

| Role | Path |
|------|------|
| `newRowSuggestId`, `mixedPromotePairs`, `importableSuggestions`, `assetQuantitiesCancel` | `frontend/src/lib/features/transactions/bulk/promoteSuggest.ts` |
| `cashAmountsCancel` | `frontend/src/lib/features/transactions/bulk/promoteHelpers.ts` |
| The editor | `frontend/src/lib/features/transactions/bulk/TransactionBulkModal.svelte` |
| «Merge all» | `frontend/src/lib/features/transactions/bulk/PromoteAllModal.svelte` |
| Vitest | `frontend/src/lib/features/transactions/bulk/promoteSuggest.test.ts` |
| E2E: same session, separate sessions, reminder, merge all | `frontend/e2e/transactions/tx-import-scalable-transfers.spec.ts` |
| E2E: the cost check on promotes | `frontend/e2e/transactions/tx-bulk-promote-cost-basis.spec.ts` |
