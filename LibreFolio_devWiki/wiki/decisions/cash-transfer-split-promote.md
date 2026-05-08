---
title: "CASH_TRANSFER + Split/Promote as immediate dedicated endpoints"
category: decision
status: resolved
date: 2026-04-30
tags: [backend, transactions, paired, split, promote, cash-transfer, enum]
related:
  - decisions/tx-link-uuid-semantics
  - decisions/unified-batch-pipeline
  - features/F-046
  - features/F-048
---

# Decision: CASH_TRANSFER + Split/Promote Immediate Endpoints

## Context
Phase 7 Part 4 Round 5 introduced dual-form mode for paired transactions. Two problems emerged:
1. Cash transfers (wire/bonifico) between brokers required a virtual WITHDRAWAL+DEPOSIT pair with type-mixing (`VALID_MIXED_PAIRS` hack). This violated the "same-type pairs" invariant.
2. Split/Promote operations are structural transformations (type mutation + link creation/removal). Deferring them in the batch `TXMixedBatch` creates an unmanageable state graph.

## Options Considered
1. **Option A** — Virtual frontend types only → rejected (backend doesn't understand paired cash semantics)
2. **Option B** — Keep WITHDRAWAL+DEPOSIT with VALID_MIXED_PAIRS → rejected (grows complexity with every new pair type)
3. **Option C (chosen)** — CASH_TRANSFER as first-class enum + split/promote as immediate endpoints

## Decision
**Option C — First-class composite types + immediate structural endpoints**.

### CASH_TRANSFER
- Added `CASH_TRANSFER` to `TransactionType` enum alongside `TRANSFER` and `FX_CONVERSION`
- `pair_form_layout="transfer_cash"`, `asset_mode="forbidden"`, `cash_mode="required"`, `quantity_mode="forbidden"`
- Removed `VALID_MIXED_PAIRS` validation hack

### Split/Promote Architecture
- **`POST /transactions/split`**: accepts `items: [{id}]`, finds partner via `link_uuid`, applies deterministic type mutation, removes link. Immediate.
- **`POST /transactions/promote`**: accepts `items: [{id_a, id_b}]`, validates compatibility via `promote_from` rules, applies type mutation, generates `link_uuid`. Immediate.
- `POST /transactions/commit` stays unchanged (creates + updates + deletes only). Clean separation.

### Type Mutation Maps
| Pair Type | Split From→ | Split To→ |
|---|---|---|
| `CASH_TRANSFER` | `WITHDRAWAL` | `DEPOSIT` |
| `TRANSFER` | `ADJUSTMENT` (-qty) | `ADJUSTMENT` (+qty) |
| `FX_CONVERSION` | `WITHDRAWAL` (neg) | `DEPOSIT` (pos) |

Promote is the inverse of split.

### Server-Driven Metadata
`TXTypeMetadata` extended with `split_into`, `promote_from`, `pair_field_constraints` — frontend reads rules instead of hardcoding.

## Consequences
- Frontend dual-form creates proper `CASH_TRANSFER+CASH_TRANSFER` pairs (not WITHDRAWAL+DEPOSIT)
- Split and promote are safe, deterministic operations — can be done from both main table and BulkModal
- No VALID_MIXED_PAIRS maintenance burden
- Backend endpoints planned but not yet implemented (schemas ready, endpoints deferred to Round 6 Plan C)

## Source files

| Role | Path |
|------|------|
| Transaction schemas | `backend/app/schemas/transactions.py` |
| Transaction service | `backend/app/services/transaction_service.py` |
| Transaction API | `backend/app/api/v1/transactions.py` |
| DB models (enum) | `backend/app/db/models.py` |
| Frontend type store | `frontend/src/lib/stores/transactionTypeStore.ts` |

