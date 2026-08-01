---
title: "Import wizard fake asset-id collision across multiple files"
category: problem
date: 2026-07-26
tags: [frontend, brim, import, asset-resolution, data-integrity]
related: [[entities/import-wizard-modal]]
---

# Import wizard fake asset-id collision across multiple files

## Summary
When several broker files are imported in one wizard session, every file's plugin
emits placeholder ("fake") asset ids counting **down from the same
`FAKE_ASSET_ID_BASE` (2147483647)**. The Step-4 merge keyed its `assetMap` by the
bare fake id, so identical fake ids from different files **collided**: the first
file's resolution won and the second file's instrument silently reused the wrong
real asset. In prod this bound all 7 Intesa patrimonio seeds (EURIZON funds, correctly
resolved per-file to assets 16–19) onto Crédit Agricole's BTP assets 31–37, producing
a nonsensical portfolio value (e.g. `BTP PIU 25-2-33 CUM` at `-917.687,72 € / -99.99%`).

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
  `selected_asset_id` null (`uniqueExactCandidateId`).
- Second, independent bug on the same asset: quantity `91.861` round-tripped to `91861`
  because the tx edit form used `<input type="number">`, which in an Italian-locale
  browser treats `.` as a thousands separator. Fixed separately (see
  [[problems/browser-autofill-numeric-fields]] / numeric inputs → `type="text"
  inputmode="decimal"` + `normalizeDecimalInput`).

## Verification
- `./dev.py front check` → 0 errors / 0 warnings.
- Trace of the exact prod fake ids confirms CA and Intesa now receive disjoint global ids.

## Source files
| Role | Path |
|------|------|
| Fix (merge + remap) | `frontend/src/lib/components/transactions/modals/ImportWizardModal.svelte` |
| Fake-id range util | `frontend/src/lib/utils/brim/isFakeAssetId.ts` |
| Decimal-input fix | `frontend/src/lib/utils/core/parseDecimalInput.ts` |
