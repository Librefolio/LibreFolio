---
title: "SafeDecimal — Preventing Scientific Notation in JSON Responses"
category: concept
tags: [backend, serialization, pydantic, decimal, json, frontend, zod]
related: [features/F-046, features/F-012]
---

# Concept: SafeDecimal — Preventing Scientific Notation in JSON Responses

## Definition

`SafeDecimal` is a Pydantic V2 annotated type that forces fixed-point notation (`format(v, 'f')`) when serializing `Decimal` values to JSON, preventing Python's default `str(Decimal)` from emitting scientific notation (e.g. `"1.29E+5"`, `"0E+6"`).

## Problem

Python's `str(Decimal)` produces scientific notation for certain values:
- `str(Decimal("1.29E+5"))` → `"1.29E+5"`
- `str(Decimal("0E+6"))` → `"0E+6"`

Pydantic V2's `model_dump(mode='json')` uses `str()` for Decimal serialization. Frontend Zod regex validators reject scientific notation → API responses fail client-side validation silently.

## Root Cause

`Decimal.normalize()` creates scientific notation (e.g. `Decimal("129000.000000").normalize()` → `Decimal("1.29E+5")`). Any arithmetic on Decimals can also produce these representations. The problem is invisible in backend tests (they compare numeric values, not string representations).

## Solution: 3-Layer Approach

1. **`SafeDecimal` type** in `backend/app/schemas/common.py` — `Annotated[Decimal, PlainSerializer(lambda v: format(v, 'f'))]` forces fixed-point notation
2. **`Currency.amount`** uses `SafeDecimal` — covers ALL currency amounts throughout the app
3. **Response schemas** use `SafeDecimal` for bare Decimal fields (`BRAssetHolding`, `TXReadItem`, etc.)

## Key Rule

> **In response schemas, ALWAYS use `SafeDecimal` instead of `Decimal`** for numeric fields that reach the frontend. Input schemas can stay `Decimal` since values come FROM the frontend.

## Where It Applies

Currently adopted in:
- `backend/app/schemas/common.py` — type definition + `Currency.amount`
- `backend/app/schemas/brokers.py` — `BRAssetHolding` fields (`quantity`, `average_cost_per_unit`, `current_price`, `unrealized_pnl_percent`)
- `backend/app/schemas/transactions.py` — `TXReadItem` fields (`quantity`, `cost_basis_override`, `value`)

**Not yet adopted** (lower risk but should be migrated when touched):
- `backend/app/schemas/prices.py`
- `backend/app/schemas/fx.py`
- `backend/app/schemas/brim.py`

## Examples

```python
from backend.app.schemas.common import SafeDecimal

class MyResponse(BaseModel):
    amount: SafeDecimal
    quantity: Optional[SafeDecimal] = None
```

## Related Cleanup

The introduction of `SafeDecimal` allowed removing a redundant `.normalize()` bandaid in `backend/app/services/broker_service.py` that was masking the problem rather than fixing serialization at the schema layer.

## Prevention

When adding new Decimal fields to response schemas, use `SafeDecimal` from the start. The type annotation is the fix — no runtime cost, no behavioral change for non-scientific values.

## Source files

| Role | Path |
|------|------|
| Type definition | `backend/app/schemas/common.py` (L50–66) |
| Broker schema adoption | `backend/app/schemas/brokers.py` |
| Transaction schema adoption | `backend/app/schemas/transactions.py` |
| Bandaid removal | `backend/app/services/broker_service.py` |

