---
title: "R2 SP-A — Cost Basis Override Currency + WAC Service + recalc-wac"
category: source
source_type: plan
date_ingested: 2026-06-01
original_path: LibreFolio_developer_journal/RoadmapV4_UI/PlanD_SplitPromoteFullStack/R2-WalktestFeedback/plan-R2-SP-A-CostBasisWAC.prompt.md
tags: [phase07, transactions, wac, cost-basis, currency, fx, backend, schema, endpoint]
related:
  - sources/r2-walktest-feedback-master
  - sources/r2-sp-b-backend-tests
  - decisions/cost-basis-currency-object
  - features/F-097
  - features/F-048
---

# Source: R2 SP-A — Cost Basis Override Currency + WAC Service

## Summary
Backend implementation plan (✅ completed, commit `92f4b1ba`) covering the fundamental breaking change: `cost_basis_override` upgraded from `SafeDecimal` to `Currency` object. Steps 1–5 of the master plan. Adds `cost_basis_currency` DB column, rewrites `compute_weighted_avg_cost` with FX cross-currency support, and introduces `POST /transactions/recalc-wac` endpoint.

## Key Takeaways

### Step 1: DB + Alembic
- New column `cost_basis_currency VARCHAR(3)` on Transaction model
- Uses `_validate_currency_field` (ISO 4217 validator pattern already in codebase)
- Added in `001_initial.py` (single-migration strategy)

### Step 2: Schema — Currency object
- `cost_basis_override: Optional[SafeDecimal]` → `Optional[Currency]` on TXCreateItem, TXUpdateItem, TXReadItem
- `TXReadItem.from_db_model()` constructs Currency from two DB fields (amount + currency)
- `TXTransferPromoteRequest` and `TXPromoteBatchItem.resolved_fields` also updated
- **Breaking change**: old `"42.50"` format → 422 validation error

### Step 3: New schemas — WACConversionInfo + WACResult
- `WACConversionInfo(tx_id, from_currency, to_currency, rate, rate_date, stale_days)`
- `WACResult(wac: Optional[Currency], conversions: list[WACConversionInfo], missing_pairs: list[str])`
- `TXBatchResultItem.wac_info: Optional[WACResult]` — present only in commit/promote response

### Step 4: Service — compute_weighted_avg_cost rewrite
- New signature: `async def compute_weighted_avg_cost(session, broker_id, asset_id, as_of_date, asset_currency) -> WACResult`
- For each BUY/TRANSFER with currency ≠ target_currency → convert via FX rate at TX date
- **If even one FX conversion fails** → `WACResult(wac=None, missing_pairs=[...])`
- Target currency logic: majority among TX → asset currency on tie → alphabetical
- `total_qty == 0` with no FX errors → `Currency(code=target, amount="0")`
- Two call-sites in `transaction_service.py` updated to handle WACResult

### Step 5: recalc-wac endpoint
- `POST /api/v1/transactions/recalc-wac` — body: `{tx_ids: list[int]}`
- Validates all TX refer to **same asset** (not necessarily same broker)
- For each TRANSFER receiver: recalculates WAC, saves, returns `WACResult`
- Lightweight endpoint with TODO for future `analytics/` category

## Source files touched
| Role | Path |
|------|------|
| DB model | `backend/app/db/models.py` |
| Alembic migration | `backend/alembic/versions/001_initial.py` |
| TX schemas | `backend/app/schemas/transactions.py` |
| Common schemas (Currency) | `backend/app/schemas/common.py` |
| TX service (WAC) | `backend/app/services/transaction_service.py` |
| FX service (rate lookup) | `backend/app/services/fx.py` |
| TX API endpoints | `backend/app/api/v1/transactions.py` |
