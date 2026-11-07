---
title: "Import wizard fake asset-id collision across multiple files"
category: problem
status: resolved
date: 2026-07-26
tags: [frontend, brim, import, asset-resolution, data-integrity]
related: [entities/import-wizard-modal]
---

# Import wizard fake asset-id collision across multiple files

## Summary
When several broker files are imported in one wizard session, every file's plugin
emits placeholder ("fake") asset ids counting **down from the same
`FAKE_ASSET_ID_BASE` (2147483647)**. The Step-4 merge keyed its `assetMap` by the
bare fake id, so identical fake ids from different files **collided**: the first
file's resolution won and the second file's instrument silently reused the wrong
real asset. In production this bound the fund positions of one broker's file (correctly
resolved per file) onto the bond assets of another broker's file, producing a nonsensical
portfolio value (a bond shown at about −99.99 %).

## Details
- Each parse response resolves its own assets correctly (`selected_asset_id` was right
  in the saved parse JSON). The bug was **only in the frontend merge**, not the backend
  or the plugins.
- Root cause: `mergeAllTransactions()` used `const assetMap = new Map<number,…>()` keyed
  by `tx.asset_id`, and `!assetMap.has(assetId)` skipped the second file's same fake id.
  Every downstream lookup (`assetResolutions.find(r => r.fakeAssetId === tx.asset_id)`,
  the import-submit remap in `buildFinalTxList`) then shared one resolution across files.
- Fix: allocate a **globally-unique fake id per (file, original fake id)** during merge
  (a `nextFakeId` counter decrementing across all files, kept inside the `isFakeAssetId`
  range), **clone each tx** before rewriting `tx.asset_id`, and key `assetMap` by the new
  id. Added defense-in-depth: auto-bind a lone EXACT-ISIN candidate when the backend left
  `selected_asset_id` null (`uniqueExactCandidateId`). *2026-11-07 lint: the merge now lives in
  `importMerge.ts` (`nextFakeId`), and the auto-bind became `uniqueCandidateId`: one distinct asset id among the
  candidates of any confidence selects it, two or more are left to the user.*
- Second, independent bug on the same asset: quantity `91.861` round-tripped to `91861`
  because the tx edit form used `<input type="number">`, which in an Italian-locale
  browser treats `.` as a thousands separator. Fixed separately (see
  [[problems/browser-autofill-numeric-fields]] / numeric inputs → `type="text"
  inputmode="decimal"` + `normalizeDecimalInput`).

## Verification
- `./dev.py front check` → 0 errors / 0 warnings.
- Trace of the exact production fake ids confirms the two files now receive disjoint global ids.

## Source files
| Role | Path |
|------|------|
| Fix (merge + remap) | `frontend/src/lib/features/transactions/import/ImportWizardModal.svelte` |
| Merge today (`nextFakeId`, `uniqueCandidateId`) | `frontend/src/lib/features/transactions/import/importMerge.ts` |
| Fake-id range util | `frontend/src/lib/features/transactions/import/isFakeAssetId.ts` |
| Decimal-input fix | `frontend/src/lib/utils/core/parseDecimalInput.ts` |
