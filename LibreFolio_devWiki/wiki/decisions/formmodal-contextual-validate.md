---
title: "FormModal sends entire bulk context to /validate for same-day dependency resolution"
category: decision
status: resolved
date: 2026-05-11
tags: [frontend, transactions, validation, formModal, bulkModal, balance-walk]
related:
  - decisions/unified-batch-pipeline
  - decisions/end-of-day-balance-check
  - concepts/validate-scheduler-pattern
  - features/F-048
---

# Decision: FormModal Context-Aware Validate (Bulk Context Passing)

## Context

FormModal (which lives inside BulkModal) was validating its single row in isolation via `/validate`. This caused false negatives when rows depend on each other within the same batch (e.g., a DEPOSIT + BUY on the same day: BUY alone fails `balanceCashNegative` but succeeds when DEPOSIT is in context). Since FormModal is never standalone (always invoked from BulkModal), single-row validation is always under-contextualized.

## Options Considered

1. **Disable FormModal validation entirely**: Only validate in BulkModal. Simple but loses real-time feedback in the form.
2. **Send entire bulk context to `/validate`**: FormModal calls `getBulkContext()` from BulkModal, merges with current row, filters issues to current row only.
3. **Client-side balance pre-check**: Complex, duplicates backend logic, error-prone.

## Decision

**Option 2**: BulkModal exposes `getBulkContextExcluding(tempId)` → returns `{creates, updates, deletes}` for all rows except the one being edited. FormModal merges this with its own payload:

```typescript
const fullPayload = {
    creates: [...bulkContext.creates, ...myPayload.creates],
    updates: [...bulkContext.updates, ...myPayload.updates],
    deletes: bulkContext.deletes,
};
```

Issues returned by `/validate` are filtered to only those matching the current row's index+operation.

## Consequences

- FormModal now sees same-day inter-dependencies correctly (DEPOSIT enables BUY)
- Contextual i18n banner header (`transactions.validate.contextualIssuesHeader`) distinguishes bulk-context errors
- Backend remains the single validator — zero logic duplication
- BulkModal's global validate remains unchanged
- 8 balance walk tests confirm end-of-day algorithm is correct

## Source files

| Role | Path |
|------|------|
| FormModal (contextual validate) | `frontend/src/lib/components/transactions/TransactionFormModal.svelte` |
| BulkModal (getBulkContextExcluding) | `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` |
| Balance walk tests | `backend/test_scripts/test_api/test_tx_balance_walk.py` |

