---
title: "CASH_TRANSFER first-class enum + Split/Promote via batch pipeline"
category: decision
status: resolved
date: 2026-04-30
tags: [backend, frontend, transactions, paired, split, promote, cash-transfer, enum, batch-pipeline]
related:
  - decisions/tx-link-uuid-semantics
  - decisions/unified-batch-pipeline
  - features/F-046
  - features/F-048
  - sources/phase07-part4-round6-pland1-backend-batch-suggest
---

# Decision: CASH_TRANSFER + Split/Promote via Batch Pipeline

## Context
Phase 7 Part 4 Round 5 introduced dual-form mode for paired transactions. Two problems emerged:
1. Cash transfers (wire/bonifico) between brokers required a virtual WITHDRAWAL+DEPOSIT pair with type-mixing (`VALID_MIXED_PAIRS` hack). This violated the "same-type pairs" invariant.
2. Split/Promote operations are structural transformations (type mutation + link creation/removal). Originally planned as immediate dedicated endpoints, but implemented directly in the batch pipeline.

## Options Considered
1. **Option A** — Virtual frontend types only → rejected (backend doesn't understand paired cash semantics)
2. **Option B** — Keep WITHDRAWAL+DEPOSIT with VALID_MIXED_PAIRS → rejected (grows complexity with every new pair type)
3. **Option C (chosen, revised)** — CASH_TRANSFER as first-class enum + split/promote through unified batch pipeline

## Decision
**Option C (revised in D1) — First-class composite types + split/promote as batch operations**.

### CASH_TRANSFER
- Added `CASH_TRANSFER` to `TransactionType` enum alongside `TRANSFER` and `FX_CONVERSION`
- `pair_form_layout="transfer_cash"`, `asset_mode="forbidden"`, `cash_mode="required"`, `quantity_mode="forbidden"`
- Removed `VALID_MIXED_PAIRS` validation hack

### Split/Promote Architecture (revised in Plan D1)
- ~~`POST /transactions/split`~~ — **ELIMINATED** (DD2 of D1: never used in production)
- ~~`POST /transactions/promote`~~ — **ELIMINATED** (DD2 of D1: never used in production)
- Split and promote now go exclusively through `TXMixedBatch`:
  - `POST /transactions/validate` — dry-run with `{splits: [{id_a, id_b}], promotes: [{id_a, id_b, resolved_fields}]}`
  - `POST /transactions/commit` — commit with same payload
- 8 orphan schemas removed (`TXSplitItem/Request/Response`, `TXPromoteItem/Request/Response`)
- Service methods `split_pairs()` and `promote_pairs()` removed — logic absorbed into pipeline Steps 5b/5c
- **`POST /transactions/promote-suggest`** — NEW: bulk candidate matching for auto-detect

### Type Mutation Maps (SPLIT_TYPE_MAP)
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
- Split and promote are atomic batch operations — can be done from both main table and BulkModal alongside other creates/updates/deletes
- No VALID_MIXED_PAIRS maintenance burden
- `consumed_link_uuids` prevents double-processing when promotes use link_uuids from creates in the same batch
- PMC (weighted average cost) auto-calculated on TRANSFER receiver when cost_basis_override is null

## Source files

| Role | Path |
|------|------|
| Transaction schemas | `backend/app/schemas/transactions.py` |
| Transaction service | `backend/app/services/transaction_service.py` |
| Transaction API | `backend/app/api/v1/transactions.py` |
| DB models (enum) | `backend/app/db/models.py` |
| Frontend type store | `frontend/src/lib/stores/transactionTypeStore.ts` |
| PromoteMergeModal | `frontend/src/lib/components/transactions/PromoteMergeModal.svelte` |
| Batch split/promote tests | `backend/test_scripts/test_api/test_transactions_batch_split_promote.py` |
