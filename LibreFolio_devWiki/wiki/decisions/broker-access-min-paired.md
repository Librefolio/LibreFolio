---
title: "Paired access level = min(role_A, role_B) + 3-layout delete"
category: decision
status: resolved
date: 2026-05-05
tags: [frontend, backend, transactions, broker-access, paired, delete, security]
related:
  - decisions/cash-transfer-split-promote
  - features/F-010
  - features/F-047
  - features/F-048
---

# Decision: Paired Access Level = min(role_A, role_B) + 3-Layout Delete

## Context
Paired transactions (TRANSFER, FX_CONVERSION, CASH_TRANSFER) span two brokers. The user may have different roles on each (OWNER, EDITOR, VIEWER, or no access). What actions should be available?

## Decision

### Paired Access Level
The access level of a paired transaction is the **minimum** of the user's role on both brokers:

```
min(OWNER, EDITOR) = full    → edit/delete/clone allowed
min(OWNER, VIEWER) = viewer  → view only
min(OWNER, null)   = none    → view only (locked partner)
```

| Level | edit | delete | clone | view |
|-------|------|--------|-------|------|
| `full` | ✅ | ✅ | ✅ | ✅ |
| `viewer` | ❌ | ❌ | ❌ | ✅ |
| `none` | ❌ | ❌ | ❌ | ✅ |

### TransactionDeleteModal — 3 Layouts
- **Layout A** (standalone): full detail recap table (Type, Date, Asset, Qty, Amount, Broker, Tags)
- **Layout B** (paired, full access): dual-column From/To recap. Always deletes both halves. Info banner: "To delete only one side, first use Split"
- **Layout C** (paired, blocked): partner inaccessible/viewer. Delete button hidden. Warning: "You need Editor access on both brokers to delete a linked pair"

### Backend Enforcement
`_check_paired_access()` added to `_update_single` and `_delete_single` — verifies EDITOR role on both brokers for paired mutations. The `pairDeleteIncomplete` validation (existing) requires both halves in delete batch.

> *2026-11-07 lint:* `_check_paired_access()`, `_update_single` and `_delete_single` no longer exist (removed with the
> WAC inline pipeline, `d3100fb44`). Access is now checked once per batch: every referenced row is loaded and its broker
> joins the touched brokers, each of which needs EDITOR (`transaction_batch_stages.py`, `access.py::_enforce_batch_access`);
> `pairDeleteIncomplete` (`batch_edits.py`) still requires both halves of a pair in a delete, so a pair delete needs
> EDITOR on both brokers. Whether a one-sided update checks the partner's broker was not verified by the lint.

### GET /brokers LEFT JOIN
Changed from INNER JOIN to LEFT JOIN so the response includes ALL brokers with `user_role=null` for inaccessible ones. Enables UI to show broker names in locked placeholders. `brokerStore` exposes `getEditableBrokers()` for form dropdowns.

### partner_broker_id
New field in `TXReadItem` — batch lookup of partner broker IDs for tooltip and form display. Enables showing "🔒 Hidden Admin Broker — not accessible" even when partner row isn't visible.

## Consequences
- Clean security model: frontend hides actions, backend enforces
- User always sees informative messages about why actions are blocked
- Split-first workflow for partial pair deletion is self-documenting via Layout B hint

## Source files

| Role | Path |
|------|------|
| Broker role helpers | `frontend/src/lib/utils/broker/brokerRoleHelpers.ts` |
| Broker store | `frontend/src/lib/stores/reference/brokerStore.ts` |
| BrokerBadge (showRole) | `frontend/src/lib/components/ui/display/BrokerBadge.svelte` |
| Transaction service | `backend/app/services/transactions/transaction_service.py` |
| Batch access stage (touched brokers, EDITOR) | `backend/app/services/transactions/transaction_batch_stages.py` |
| Access helpers | `backend/app/services/transactions/access.py` |
| `pairDeleteIncomplete` | `backend/app/services/transactions/batch_edits.py` |
| Transaction schemas | `backend/app/schemas/transactions/transactions.py` |
| Delete flow (TransactionDeleteModal removed 2026-09-03: single-row delete routes through the bulk workspace) | `frontend/src/lib/features/transactions/bulk/TransactionBulkModal.svelte` |
| Broker service | `backend/app/services/brokers/broker_service.py` |

