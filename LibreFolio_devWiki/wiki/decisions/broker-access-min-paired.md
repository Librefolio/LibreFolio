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
| Broker role helpers | `frontend/src/lib/utils/brokerRoleHelpers.ts` |
| Broker store | `frontend/src/lib/stores/brokerStore.ts` |
| BrokerBadge (showRole) | `frontend/src/lib/components/ui/BrokerBadge.svelte` |
| Transaction service | `backend/app/services/transaction_service.py` |
| Transaction schemas | `backend/app/schemas/transactions.py` |
| Delete modal | `frontend/src/lib/components/transactions/TransactionDeleteModal.svelte` |
| Broker service | `backend/app/services/broker_service.py` |

