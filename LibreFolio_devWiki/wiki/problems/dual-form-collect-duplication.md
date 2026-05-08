---
title: "Dual-form collect logic duplication causing cascading bugs"
category: problem
status: resolved
date: 2026-05-05
tags: [frontend, transactions, dual-form, code-duplication, formModal, bulkModal]
related:
  - features/F-048
  - decisions/dual-transaction-form-design
---

# Problem: Dual-Form Collect Logic Duplication

## Symptom
Three consecutive bugs in Phase 7 Part 4 Round 5–6 traced to the same root cause:
1. **R7-C1**: Edit paired creates partner as new instead of update
2. **R7-H1**: Type swap qty doesn't propagate in table
3. **Qty/description diff spurio**: Changed only date, but qty and description appear in payload

## Root Cause
`TransactionFormModal.svelte` and `TransactionBulkModal.svelte` had completely independent implementations of the same transaction payload logic:

| Function | BulkModal | FormModal | Divergence |
|----------|-----------|-----------|------------|
| `collectCreate` | `applySignRules()` | inline `autoNegateQty/Cash` | Same logic, different impl |
| `collectUpdate` | `diffFields()` + `PATCHABLE_FIELDS` | inline field-by-field | **Caused R7-H1** |
| `collectDualUpdates` | N/A | `collectDualCreates()` wrapping | **Caused R7-C1** |
| `PATCHABLE_FIELDS` | line 590 | line 890 | **Literal duplicate** |
| `fieldEq`/`diffFields` | `jsonEq`/`nullishEq` | `fieldEq` with numeric normalisation | **Different comparison** |

## Solution
Created `frontend/src/lib/utils/txPayloadHelpers.ts` — single shared module:
1. `PATCHABLE_FIELDS` — one canonical copy
2. `applySignRules(qty, cash, typeRule)` — pure sign-flip function
3. `buildCreatePayload(fields, typeRule)` — constructs `TXCreateItem`
4. `buildUpdateDiff(current, original, currentRule, originalRule)` — diff with numeric normalisation, filtered by PATCHABLE_FIELDS
5. `fieldEq(key, a, b)` — type-aware normalised comparison (numbers as `Number()`, cash as numeric amount + strict code, tags as sorted array, strings normalise null/undefined/"")

Both FormModal and BulkModal now import from this single source.

## Prevention
Any time two components need identical business logic for payload construction, extract to a shared utility immediately — don't let parallel inline implementations accumulate.

## Impact
~4h of debugging across 3 rounds (R7-C1, R7-H1, diff spurio). Each fix revealed the next manifestation of the same root cause until the shared helper was created.

## Source files

| Role | Path |
|------|------|
| Shared helpers | `frontend/src/lib/utils/txPayloadHelpers.ts` |
| FormModal | `frontend/src/lib/components/transactions/TransactionFormModal.svelte` |
| BulkModal | `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` |

