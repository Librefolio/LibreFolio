---
title: "WAC Inline in Validate/Commit — No Standalone WAC Endpoint in Editing Flow"
category: Decision
status: Resolved
date: 2026-05-28
tags: [backend, frontend, transactions, wac, architecture, api]
related_features: [F-097, F-048]
related_problems: [problems/wac-feedback-loop]
---

# WAC Inline in Validate/Commit

## Context

The initial WAC architecture used a standalone `POST /transactions/wac-preview` endpoint. The frontend called it reactively when fields changed. This caused:
1. **Feedback loops** (WAC result → field change → new WAC request)
2. **Stale previews** (WAC computed against old DB state, not pending workspace state)
3. **Extra network calls** (separate from validate, duplicating batch payload construction)

## Decision

Eliminate the standalone WAC endpoint from the editing workflow. WAC is computed:
- **In `/validate` response**: `wac_results: WACPreviewResultItem[]` — frontend shows preview
- **In `/commit` post-flush**: backend applies WAC autonomously using actual DB state

The standalone `/wac-preview` endpoint is repurposed as `/analytics/wac` for historical time-series queries (Phase 9, not part of editing flow).

## Alternatives Considered

| Option | Verdict | Reason |
|--------|---------|--------|
| Keep standalone `/wac-preview` + frontend guard | ❌ | Feedback loop fundamental, not fixable with guards |
| Compute WAC client-side | ❌ | Requires all historical TX data on client; violates backend-only-calculations principle |
| Compute WAC at commit only (no preview) | ❌ | Users need to see WAC before committing to validate their input |
| **WAC in validate + apply in commit** | ✅ | Preview without loops; apply with correct DB state |

## Implementation

### Validate path (preview):
```
POST /validate → execute_batch(dry_run=True)
  → Step 6b: _compute_wac_for_auto_items()
  → Returns: {results: [...], wac_results: [...]}
```

### Commit path (apply):
```
POST /commit → execute_batch(dry_run=False)
  → flush() → all rows in DB (session-level)
  → Step 6b: _compute_wac_for_auto_items()
    → compute_wac_iterative() queries same session → sees ALL pending changes
    → Writes cost_basis_override directly on receiver TX
  → balance_walk → rollback if fails (wac_results still in response)
```

### Key insight: post-flush computation
After flush, all batch items exist in the DB session (not committed to disk yet). `compute_wac_iterative` does normal DB queries on the same session → sees everything. No adapter needed to convert batch items to pending_txs.

### `cost_basis_mode` semantics
- `'auto'` — backend computes WAC and applies it
- `'manual'` — user's `cost_basis_override` value used as-is
- `'auto-detail'` — same as auto, but frontend shows expanded qualifying table
- Mode is NOT persisted to DB. After commit, the TX has only `cost_basis_override` (the computed value). On re-edit, frontend shows 'manual' if value exists.

## Consequences

- **Positive**: Zero feedback loops; preview always reflects current workspace state; one fewer endpoint to maintain
- **Positive**: WAC result available even if balance validation fails (computed before balance walk)
- **Negative**: Validate response is heavier (includes wac_results). Acceptable trade-off.
- **Negative**: Cannot preview WAC without triggering full validate. Acceptable because validate is already called reactively.

## Source files

| Role | Path |
|------|------|
| execute_batch (WAC computation) | `backend/app/services/transaction_service.py` |
| WAC schemas | `backend/app/schemas/transactions.py` |
| Frontend validate handler | `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` |
| WacPreviewSection (display) | `frontend/src/lib/components/transactions/WacPreviewSection.svelte` |
