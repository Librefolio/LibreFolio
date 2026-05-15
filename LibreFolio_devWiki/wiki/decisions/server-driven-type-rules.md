---
title: "Server-Driven Type Rules — replace hardcoded frontend files"
category: decision
status: resolved
date: 2026-04-30
tags: [backend, frontend, transactions, type-rules, architecture, auto-sign]
related: [features/F-046, features/F-048, decisions/unified-batch-pipeline]
---

# Decision: Server-Driven Type Rules

## Context

Transaction type rules (which fields are required/optional/forbidden, quantity/cash signs, event compatibility) were duplicated between the backend (`TXCreateItem.validate_transaction_rules`) and 3 hardcoded frontend files (`transactionTypeRules.ts`, `transactionTypes.ts`, `eventTypes.ts`). Adding a new transaction type required changes in both layers.

## Options Considered

1. **Keep frontend hardcoded** — fast to implement but maintenance burden grows.
2. **Server-driven via `GET /transactions/types`** — backend is single source of truth; frontend auto-adapts. ✅ Selected.

## Decision

Replace 3 frontend files with a single `transactionTypeStore.ts` that fetches from `GET /transactions/types`. Backend sends `TXTypesResponse`:

```python
class TXTypeMetadata(BaseModel):
    code: str                         # "BUY", "SELL", etc.
    name: str                         # English name
    icon_slug: str                    # "buy" → /icons/transactions/buy.png
    doc_slug: Optional[str]           # "buy-sell" → mkdocs page
    asset_mode: FieldMode             # required | optional | forbidden
    cash_mode: FieldMode              # required | optional | forbidden
    quantity_mode: FieldMode          # required | optional | forbidden
    quantity_sign: SignRule            # positive | negative | zero | nonzero | free
    cash_sign: SignRule               # positive | negative | zero | nonzero | free
    requires_link: bool               # TRANSFER, FX_CONVERSION
    event_compatible: bool            # DIVIDEND, INTEREST, ADJUSTMENT
    pair_form_layout: Optional[PairFormLayout]  # fx | transfer_asset | transfer_cash | null

class EventTypeMetadata(BaseModel):
    code: str; name: str; emoji: str; compatible_tx_types: List[str]

class TXTypesResponse(BaseModel):
    transaction_types: List[TXTypeMetadata]
    event_types: List[EventTypeMetadata]
```

Frontend uses server data **as-is** with zero mapping functions (all values lowercase).

**Auto-sign negation**: when `SignRule === "negative"`, user enters positive numbers → frontend auto-negates in `collectCreate()`/`collectUpdate()`. Visual hint "(−)" on label.

## Consequences

- Single source of truth in backend for type rules
- Adding a new transaction type requires only backend changes
- Frontend `transactionTypeRules.ts`, `transactionTypes.ts`, `eventTypes.ts` deleted
- Auto-sign negation improves UX (no negative number entry)
- `pair_form_layout` enables dual-transaction form for FX/Transfer types

## Source files

| Role | Path |
|------|------|
| Backend metadata | `backend/app/schemas/transactions.py` (TXTypeMetadata, EventTypeMetadata, TXTypesResponse) |
| Frontend store | `frontend/src/lib/stores/transactionTypeStore.ts` |
| Source plan | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round4-5/plan-phase07-transaction-Part4_Round5_ServerDrivenTypeRules.prompt.md` |

