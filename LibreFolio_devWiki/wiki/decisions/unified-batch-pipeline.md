---
title: "Unified Batch Pipeline — 2 endpoints replace 4"
category: decision
status: resolved
date: 2026-04-29
tags: [backend, transactions, api, validation, breaking-change, architecture]
related: [decisions/multi-broker-atomic-tx, features/F-046, sources/phase07-part4-round4-pipeline]
---

# Decision: Unified Batch Pipeline

## Context

FastAPI deserialises `List[TXCreateItem]` automatically before the endpoint handler runs. If any row has a Pydantic schema error, the entire request returns HTTP 422 and the handler never executes — meaning balance validation (which runs inside `validate_batch`) is invisible. Schema errors and balance violations could never coexist in the same response (W21/W22/W23).

## Options Considered

1. **Raw JSON + lenient parse (Option A)** — accept `List[dict]`, parse per-row in service. ✅ Selected (combined with C).
2. **Exception handler middleware (Option B)** — intercept `RequestValidationError` globally. ❌ Fragile, can't do balance validation on valid rows.
3. **Validate-then-commit (Option C)** — bulk commit calls `validate_batch` as pre-check. ✅ Combined with A.

## Decision

Merge 4 endpoints into 2, sharing a single `TXMixedBatch` body with `List[dict]`:

| Endpoint | Semantics |
|----------|-----------|
| `POST /transactions/validate` | Dry-run: always rollback |
| `POST /transactions/commit` | Commit if clean, rollback otherwise |

Internal pipeline: `_parse_lenient()` does per-row `Model.model_validate(raw)` in try/except → collects schema errors → continues with valid rows for access check + apply + balance walk → returns unified `TXBatchResponse { committed, issues, results }`.

**Removed**: `POST /bulk`, `PATCH /bulk`, `DELETE /bulk`.

## Consequences

- Schema + business + balance errors coexist in one response
- Creates + updates + deletes in same request (mixed batch)
- Single pipeline for all tx mutations (`execute_batch`)
- Frontend simplified: 1 commit endpoint, 1 preview endpoint
- HTTP 200 always (committed=false is semantic, not an error)
- Net −290 lines backend, 7 deprecated schemas deleted

## Source files

| Role | Path |
|------|------|
| Pipeline implementation | `backend/app/services/transaction_service.py` |
| Endpoint definitions | `backend/app/api/v1/transactions.py` |
| Schema definitions | `backend/app/schemas/transactions.py` |
| Source plan | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round4-5/plan-phase07-transaction-Part4_Round4_UnifiedBatchPipeline.prompt.md` |

