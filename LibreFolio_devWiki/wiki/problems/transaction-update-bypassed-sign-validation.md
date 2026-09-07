---
title: "Transaction UPDATE could persist positive FEE/TAX (sign validation gap)"
category: "problem"
status: resolved
date: 2026-07-22
tags: ["backend", "validation", "transactions", "fee", "tax", "data-quality"]
related: ["decisions/fifo-v4-validation-and-scope", "entities/fifo-lot-engine"]
---

# Problem: Transaction UPDATE could persist positive FEE/TAX

## Symptom
CREATE and BRIM import correctly enforced that `FEE`/`TAX` transaction amounts must be negative (costs reduce
cash), but a PATCH/UPDATE on an existing transaction could persist a **positive** FEE/TAX amount — a value the
FIFO cost math assumes can never happen (it derives positive cost magnitudes from `-amount`).

## Root Cause
`TXUpdateItem`'s validation only checked `id > 0`; the update path wrote the raw patched cash amount straight
through without re-validating the **final, merged** transaction state (existing fields + patch) against the
same business rules CREATE enforces.

## Solution
Factored the sign/business-rule validation into a shared validator and made the UPDATE path call it against
the final merged state **before** persisting, not just against the raw patch. Added test coverage for the
CREATE/UPDATE sign rule (`test_transactions_validate.py`). Also added a one-off read-only diagnostic script
(`audit_transaction_signs.py`) to check whether any legacy data or historical direct-ORM writes had already
violated the assumption — it found zero anomalies in the real DB.

## Prevention
Any partial-update (PATCH) endpoint that has business-rule invariants enforced on CREATE needs those same
invariants re-checked against the **post-merge** state, not just against the fields present in the patch
payload — a valid patch can still produce an invalid final row. A DB-level `CHECK` constraint was considered
as a stronger guarantee but rejected as fragile when coupled to an enum/type column (see
[[decisions/fifo-v4-validation-and-scope]]); the chosen defense is API-layer validation plus an internal
diagnostic sign guard, not a hard schema constraint.

## Impact
Downstream FIFO fee/tax math assumes costs are positive magnitudes derived from negative transaction amounts;
an unnoticed positive FEE/TAX from this gap would have silently corrupted per-lot cost allocation math. Fixed
before release, zero anomalies found in existing data.

## Source files
| File |
|------|
| `backend/app/schemas/transactions.py` |
| `backend/app/services/transaction_service.py` |
| `backend/test_scripts/test_db/audit_transaction_signs.py` |
| `backend/test_scripts/test_api/test_transactions_validate.py` |
| `LibreFolio_developer_journal/RoadmapV4_UI/fifo-engine/v4-fee_tax_integration/feasibility-analysis-v4.1.md` §5.2-5.6 |
