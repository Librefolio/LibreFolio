---
title: "Transaction Link UUID Semantics (TRANSFER/DEPOSIT/WITHDRAWAL/FX_CONVERSION)"
date: 2026-04-21
status: resolved
tags: [transactions, transfer, linking, link_uuid]
related_features: [F-046, F-051]
related_sources: [sources/phase07-part3-api-consolidation]
---

# Decision: Transaction link_uuid Semantics

## Context

Phase 07 Part 1 introduced `link_uuid` as a mechanism for pairing linked transactions
(primarily TRANSFER). Part 3 Blocco H extended and formalized the semantics after
four design questions surfaced during code review.

## Decisions

### 1. TRANSFER requires distinct brokers

A TRANSFER pair must reference two **different** brokers. A TRANSFER within the same
broker is a semantic no-op (not meaningful for portfolio tracking). Validation added
to `create_bulk`: if both items in a `link_uuid` pair have the same `broker_id` and
type is TRANSFER → validation error.

### 2. FX_CONVERSION is intra-broker

FX_CONVERSION (currency swap on a multi-currency account, e.g., Revolut) stays
intra-broker by design. No restriction added — two FX_CONVERSION legs on the same
broker are valid.

### 3. DEPOSIT/WITHDRAWAL soft linking

Cash transfers between brokers ("I moved 5k EUR from Fineco to IBKR") are represented
as two separate DEPOSIT/WITHDRAWAL transactions linked by `link_uuid`. This produces
a bidirectional `related_transaction_id` reference.

**No new transaction type** (`CASH_TRANSFER` was considered and rejected):
- No effect on FIFO cost basis
- No effect on balance calculations (DEPOSIT in + WITHDRAWAL out already balance)
- Adds cognitive overhead for limited benefit
- The link is purely a UI/refinement hint

### 4. Transfer suggest: no dedicated endpoint

`POST /transactions/transfers/suggest` was considered and **rejected**. Instead,
`GET /transactions` was extended with 3 new filters:
- `amount_abs_min` / `amount_abs_max` (absolute value range — finds opposite-sign matches)
- `only_unlinked` (exclude already-paired transactions)
- `exclude_ids` (exclude known IDs)

The client calculates parameters from the "seed" transaction and gets the candidate list.
More composable, less API surface.

### 5. Promote endpoint

`POST /transactions/transfers/promote` — atomic conversion of a DEPOSIT/WITHDRAWAL pair
into a TRANSFER or FX_CONVERSION pair:

```
validate pair → delete pair → create pair with new type + link_uuid
```

Uses the same `create_bulk` logic internally. Useful during BRIM refinement when an
imported DEPOSIT/WITHDRAWAL pair is later recognized as an inter-broker transfer.

## Type pairing rules (summary)

| Type | Must link to | Same broker? |
|------|-------------|:------------:|
| TRANSFER | TRANSFER | ❌ different broker required |
| FX_CONVERSION | FX_CONVERSION | ✅ same broker OK |
| DEPOSIT | WITHDRAWAL | ✅ or ❌ |
| WITHDRAWAL | DEPOSIT | ✅ or ❌ |

## Source files

| Role | Path |
|------|------|
| Transaction service (link_uuid validation) | `backend/app/services/transaction_service.py` |
| Transaction API | `backend/app/api/v1/transactions.py` |
| Transfer promote endpoint | `backend/app/api/v1/transactions.py` |
