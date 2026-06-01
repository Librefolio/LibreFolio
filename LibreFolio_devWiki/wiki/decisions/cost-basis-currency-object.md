---
title: "cost_basis_override as Currency object (not bare decimal)"
category: decision
date: 2026-05-24
status: resolved
tags: [transactions, cost-basis, currency, schema, breaking-change, wac]
related_features: [F-097, F-048]
related_decisions: [decisions/unified-batch-pipeline]
---

# Decision: cost_basis_override as Currency Object

## Context
The `cost_basis_override` field on transactions was originally a bare `SafeDecimal` (e.g., `"42.50"`). This created an ambiguity: which currency does that amount refer to? For single-currency portfolios this was implicit (same as asset currency), but for multi-currency WAC calculations the system needs to know the exact currency of each cost basis value to perform FX conversions.

## Problem
When computing weighted average cost across BUY transactions in different currencies (e.g., EUR + USD), the system must:
1. Know the currency of each BUY's cost contribution
2. Convert to a common target currency via FX rates
3. Store the result with explicit currency information

A bare decimal cannot carry this information.

## Decision
Replace `cost_basis_override: Optional[SafeDecimal]` with `cost_basis_override: Optional[Currency]` where `Currency = {code: str, amount: SafeDecimal}`.

### Schema change
```python
# Before
cost_basis_override: Optional[SafeDecimal] = Field(...)

# After
cost_basis_override: Optional[Currency] = Field(
    default=None,
    description="Frozen cost basis for TRANSFER_IN. Object {code, amount}.",
)
```

### DB change
New column `cost_basis_currency VARCHAR(3)` alongside existing `cost_basis_override DECIMAL`. The ORM field uses `_validate_currency_field` (ISO 4217).

## Alternatives considered
1. **Infer currency from asset** — rejected because an asset's BUYs can span multiple currencies
2. **Separate `cost_basis_currency` schema field** — rejected for DX reasons; Currency object is cleaner in API payloads
3. **Backward-compatible dual format** (accept both string and object) — rejected to avoid ambiguity and keep validation simple

## Consequences
- **Breaking change**: old format `"42.50"` → 422 validation error. No backward compatibility.
- All frontend code must send `{code: "EUR", amount: "42.50"}` instead of `"42.50"`
- `./dev.py api sync` regenerates Zodios client with new Currency type for cost_basis
- Enables WAC cross-currency calculations (F-097)
- `TXReadItem.from_db_model()` constructs Currency from two DB columns

## Implementation
- Commit: `92f4b1ba` (SP-A)
- Files: `backend/app/db/models.py`, `backend/app/schemas/transactions.py`, `backend/alembic/versions/001_initial.py`

## Source files

| Role | Path |
|------|------|
| DB model (cost_basis fields) | `backend/app/db/models.py` |
| TX schemas (Currency field) | `backend/app/schemas/transactions.py` |
| Currency class definition | `backend/app/schemas/common.py` |
| Alembic migration | `backend/alembic/versions/001_initial.py` |
