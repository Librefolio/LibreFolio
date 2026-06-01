---
title: "WAC Feedback Loop — Infinite Recalculation Cycle"
category: Problem
status: resolved
date_encountered: 2026-05-28
date_resolved: 2026-05-28
severity: critical
tags: [frontend, wac, reactivity, infinite-loop, svelte5, bulkModal]
related_features: [F-097, F-048]
related_decisions: [decisions/wac-inline-validate-commit]
related_problems: [problems/svelte5-effect-read-write-loop]
---

# WAC Feedback Loop — Infinite Recalculation Cycle

## Problem Description

The WAC (Weighted Average Cost) auto-calculation in BulkModal entered an infinite loop:

```
WAC recalc → writes cost_basis_override to cell → triggers fingerprint change
→ re-triggers WAC recalc → writes cost_basis_override → triggers fingerprint change → ∞
```

This is a specific instance of the broader [[problems/svelte5-effect-read-write-loop]] pattern, but with a cross-system twist: the loop spans frontend state (fingerprint) → network call (WAC endpoint) → state mutation (write result) → fingerprint change.

## Root Cause

The WAC fingerprint included `cost_basis_override` as a material field. When auto-calc wrote the WAC result into `cost_basis_override`, the fingerprint changed, triggering a new WAC request. The response returned the same value, but the write still triggered a new cycle because the fingerprint comparison happened *before* the write was idempotent-checked.

### Secondary Problem: Interdependent Items

TRANSFER pairs where both sides have `auto` mode are circular:
- Receiver WAC depends on giver's `cost_basis_override` (for FX conversion)
- If giver is also auto → depends on receiver → deadlock

## Solution

Added explicit `cost_basis_mode: 'auto' | 'manual'` field to `WACPendingTXItem`:

1. **Backend math engine**: New mode `add_at_wac` — when receiver is `auto`, backend adds the quantity at the current WAC (algebraically proven to not change WAC: `new_wac = ((wac × qty) + (wac × new_qty)) / (qty + new_qty) = wac`)
2. **Frontend**: Sends `cost_basis_mode` in payload instead of writing result to `cost_basis_override` pre-commit
3. **Fingerprint**: No longer includes the computed WAC value — only user-editable fields trigger recalc

### Why `add_at_wac` is correct

For a TRANSFER_IN with `cost_basis_mode: 'auto'`:
```
new_wac = ((wac × qty) + (wac × transfer_qty)) / (qty + transfer_qty)
        = wac × (qty + transfer_qty) / (qty + transfer_qty)
        = wac  ← unchanged
```

The position grows but the average cost doesn't change. This is the correct PMC (Prezzo Medio di Carico) behavior for internal transfers.

## Impact

- **Before fix**: BulkModal froze on any paired TRANSFER with auto cost-basis
- **After fix**: WAC preview works reactively without loops
- **Test coverage**: E2E WB6 + WB7 specifically test auto-mode TRANSFER scenarios

## Key Takeaway

**Never let a computed result be an input to its own computation trigger.** The fix pattern is: separate "what to compute" (mode field) from "computed result" (display-only value). The computation happens server-side where idempotency is guaranteed.

## Source files

| Role | Path |
|------|------|
| Backend WAC pending schema | `backend/app/schemas/transactions.py` |
| Backend math engine | `backend/app/utils/financial_utils.py` |
| Backend WAC iterative | `backend/app/services/transaction_service.py` |
| Frontend BulkModal | `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` |
| E2E WAC tests | `frontend/e2e/transactions/tx-wac-bulk.spec.ts` |
