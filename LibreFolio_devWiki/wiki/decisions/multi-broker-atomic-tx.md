---
title: "Multi-Broker Atomic Transactions (not broker-scoped)"
date: 2026-04-20
status: resolved
tags: [transactions, api, architecture, atomicity]
related_features: [F-046, F-048, F-049]
related_sources: [sources/phase07-part3-api-consolidation]
---

# Decision: Multi-Broker Atomic Transactions

## Context

The original Phase 07 plan scoped bulk transaction endpoints to individual brokers:
`POST /brokers/{broker_id}/transactions/bulk`. Any item with a `broker_id` different
from the URL path would be immediately rejected.

## Problem Discovered

A DEFERRABLE FK constraint (`link_uuid → related_transaction_id`) requires that
cross-broker TRANSFER pairs be inserted in the **same DB session**. The existing
test `test_query_linked_tx_both_have_related_id` already demonstrated this: it creates
a TRANSFER across `test_broker` and `test_broker_overdraft` in a single `create_bulk`
call — a valid real-world scenario.

Additionally, BRIM parsing a single file may naturally produce transactions for multiple
brokers (multi-broker file), and the staging commit should be one atomic operation.

## Decision

Bulk endpoints are **not broker-scoped**. They accept items across multiple brokers:

```
POST   /transactions/bulk     (create)
PATCH  /transactions/bulk     (update)
DELETE /transactions/bulk?ids=...
POST   /transactions/validate (dry-run — mixed create+update+delete)
```

### Atomicity rules
- Each distinct `broker_id` in the batch → EDITOR access check
- `_validate_broker_balances` called **per broker** in the batch
- Any violation (FK, balance, access, broker mismatch on update) → **total rollback**
  + `rolled_back=True` in response
- Per-item `status: Literal["success","simulated","failed","not_attempted"]`
  (`success` field kept for backward-compatible simple checks)

### Removed
- `GET /transactions/{tx_id}` — replaced by `GET /transactions?ids=1,2,3`
  (ordered by ids param, still filtered to accessible brokers)

## Alternatives Considered

- **Keep broker-scoped endpoints, add separate cross-broker endpoint**: rejected.
  Adds complexity without benefit; the BRIM commit case alone justifies unified endpoints.

- **Separate TRANSFER creation endpoint**: rejected. Standard `create_bulk` already
  handles the pairing logic via `link_uuid` resolution. A dedicated endpoint would
  duplicate that logic.

## Implications

- Frontend (Staging Modal, Part 4/5): must pass all transactions in a single batch,
  including cross-broker pairs. Should show per-broker balance previews.
- Access control: checked at batch level, not per-item, but must verify EDITOR for
  each broker touched.
- Tests: cross-broker TRANSFER scenarios must be tested in the same `create_bulk` call.

## Source files

| Role | Path |
|------|------|
| Transaction service | `backend/app/services/transaction_service.py` |
| Transaction API | `backend/app/api/v1/transactions.py` |
