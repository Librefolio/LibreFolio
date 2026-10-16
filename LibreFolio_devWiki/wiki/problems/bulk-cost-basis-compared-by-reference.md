---
title: "The bulk editor marked untouched rows with a manual cost as modified: fieldEq compared cost objects by reference"
category: problem
status: resolved
date: 2026-10-10
tags: [frontend, bulk-editor, cost-basis, equality, decimal, workstream-p, release-1.2]
related:
  - decisions/transfer-pair-same-asset-opposite-quantity
  - decisions/bulk-pairs-new-with-saved
  - sources/phase00-promote-pair-checks-2026-10
---

# Problem: equal costs compared as different

## Symptom

Opening the bulk editor on two saved rows with a manual cost basis, and touching nothing: «Save» was active, «Undo all»
was visible, and the validate sent two updates that changed nothing (E2E **WB11**, `tx-wac-bulk.spec.ts`). Reported by
workstream S's test author while writing PC2 (plan 37), confirmed by P's reds on 2026-10-10.

## Root Cause

`fieldEq` (`txPayloadHelpers.ts`) compared `cost_basis_override` with `(a || '') === (b || '')` — on `{code, amount}`
objects — so two equal costs were always different. `buildUpdateDiff` and `diffDualItem` use it. It dated from
`7f1a6ed39` (2026-05-05); no existing test compared two costs.

## Solution

Commit `7f8233c47` (train 34): a branch of `fieldEq` for `cost_basis_override` (`costBasisValue`). An absent value, or one
whose amount is empty or blank, means «no cost»; otherwise the `code` and the amount compare with `exactDecimalEqual`, as
for `cash`. `description` stays a string comparison.

## Prevention

Eight red unit tests in `txPayloadHelpers.test.ts` (equal by value — `'10'` against `'10.000000'`, or a copy — and an
empty or blank amount against `null`; no equal cost sent by `buildUpdateDiff` or `diffDualItem`), and WB11. The risk
checked before the fix: a spec that opened rows with a manual cost and saved without changes would have passed only
thanks to the defect; none was found.

## Impact

Untouched rows were sent as updates: a misleading «Save», and no-op writes on every save from the editor.

## Source files

| Role | Path |
|------|------|
| `fieldEq`, `costBasisValue`, `buildUpdateDiff`, `diffDualItem` | `frontend/src/lib/features/transactions/txPayloadHelpers.ts` |
| Unit tests | `frontend/src/lib/features/transactions/txPayloadHelpers.test.ts` |
| WB11 | `frontend/e2e/transactions/tx-wac-bulk.spec.ts` |
