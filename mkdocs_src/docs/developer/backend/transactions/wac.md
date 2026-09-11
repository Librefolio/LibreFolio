# ⚖️ WAC & Cost Basis

**WAC (Weighted Average Cost)** — also called *PMC* (*Prezzo Medio di
Carico*) — is LibreFolio's blended, per-unit cost-basis method. The asynchronous
preparation layer lives in `backend/app/services/portfolio_service.py`; the pure
math layer lives in `backend/app/utils/financial/wac_utils.py`.

---

## 🏗️ Two-layer Architecture

```text
compute_wac_iterative()          ← database, split-event, FX, and cache layer
    └─ compute_wac_from_txlist() ← pure iterative math layer
```

| Layer | Responsibility |
|-------|----------------|
| `compute_wac_iterative()` | Query relevant rows, detect split-linked adjustments, choose the target currency, resolve FX, cache by transaction fingerprint, and build the response schema |
| `compute_wac_from_txlist()` | Sort and process already-normalized inputs without database or network I/O |

---

## ⚙️ Async Preparation

```python
async def compute_wac_iterative(
    session: AsyncSession,
    broker_id: int,
    asset_id: int,
    as_of_date: date,
    asset_currency: str,
    excluded_tx_ids: list[int] | None = None,
    target_currency_override: str | None = None,
) -> WACPreviewResultItem:
```

The function:

1. queries non-zero-quantity transactions for the broker and asset through
   `as_of_date`;
2. excludes any IDs supplied by the caller;
3. identifies `ADJUSTMENT` rows linked to a `SPLIT` `AssetEvent`;
4. fingerprints the selected rows and split linkage for the WAC cache;
5. chooses `target_currency_override`, or the most recent acquisition currency
   with `asset_currency` as fallback;
6. converts acquisition costs into the target currency;
7. returns `wac=None` plus `wac_missing_pairs` if required FX data is unavailable;
8. delegates the normalized rows to `compute_wac_from_txlist()`; and
9. returns a `WACPreviewResultItem`.

---

## 🧮 Pure WAC Algorithm

The pure function maintains a quantity pool and a per-unit average:

```text
For each date:
  process positive quantities before negative quantities

For an acquisition:
  new_wac = (old_qty × old_wac + added_qty × unit_cost) / new_qty

For a reduction:
  reduce quantity at the current WAC; WAC itself does not change

When quantity reaches zero:
  reset WAC to zero
```

The input is sorted by `(date, tx_id)`, then same-day additions are processed
before reductions. A negative quantity caused by rounding is clamped to a
zero-quantity, zero-WAC pool.

Split-linked adjustments bypass normal add/reduce math:

```text
new_qty = old_qty + split_delta
new_wac = (old_wac × old_qty) / new_qty
```

This preserves total economic cost while rescaling the number of units.

---

## 🧾 Persisted Cost Basis

`transactions.cost_basis_override` is a **per-unit** amount, not a total
acquisition cost. Its currency is stored in `cost_basis_currency`; the two values
are written and cleared together by the transaction flows.

| Field | Meaning |
|-------|---------|
| `cost_basis_override` | Frozen WAC for one unit |
| `cost_basis_currency` | ISO currency code for that per-unit amount |

For a positive incoming `TRANSFER` or `ADJUSTMENT`, the portfolio calculation
uses the override as the acquisition unit cost. A normal `BUY` derives its unit
cost from the absolute cash amount divided by quantity. If an acquisition has
neither a usable override nor a purchase amount, the pure engine treats it as a
zero-cost addition.

---

## 🔄 Inline Batch Auto Modes

`cost_basis_mode` is a request-only instruction on `TXCreateItem` and
`TXUpdateItem`; it is not a database column.

| Mode | Batch behavior |
|------|----------------|
| `auto` | Compute and persist the per-unit WAC; return a compact WAC result |
| `auto-detail` | Compute the same value and also return qualifying transactions and price detail |
| `manual` | Use the submitted `cost_basis_override`; do not add the row to the auto-WAC worklist |

The ordered batch flow is:

```text
create → promote → link resolution → compute_wac_and_fx_issues()
       → validate required cost basis → balance replay
```

`compute_wac_and_fx_issues()` calls
`TransactionService._compute_wac_for_auto_items()` only when no non-balance issue
already exists. That helper scans only `parsed_creates` and `parsed_updates` for
`auto` or `auto-detail`.

For each selected row:

- a create carrying `link_uuid` uses the linked partner's broker as the WAC
  source;
- an unlinked item uses its own broker and excludes its own row from the WAC
  history;
- a supplied `cost_basis_override.code` acts as the target-currency hint; and
- a calculated `wac` is written to `cost_basis_override` and
  `cost_basis_currency` on the staged ORM row.

The create stage has already flushed new rows for generated IDs, and all of this
work remains in the caller's session. Neither the WAC helper nor the surrounding
batch stages commit.

### 🧬 Split-linked adjustment skip

If the selected row references an `AssetEvent` of type `SPLIT`, auto mode clears
both stored cost-basis fields and emits a batch WAC result with `wac=None` and no
missing pairs. The portfolio math will rescale the live pool when it later sees
the split-linked adjustment; storing the pre-split WAC would double-count the
economic cost.

### 💱 Missing FX behavior

If `compute_wac_iterative()` returns no WAC and reports missing FX pairs, the
batch stage appends a `TXValidationIssue` with:

- code `wacFxUnavailable`;
- the originating create/update operation and index;
- field `cost_basis_override`; and
- pair names plus required dates in `params`.

The response may still include `wac_results`, but the issue makes
`committed=False`; the route that owns the session then rolls back.

### 🔗 Promote boundary

`TXPromoteBatchItem` has no `cost_basis_mode`, and `apply_promotes()` no longer
performs an automatic WAC calculation. A promote-specific resolved value arrives
as `resolved_fields.cost_basis_override` from the frontend merge flow (or another
API client). The promote stage applies it to the positive-quantity transfer leg
and clears it from the sender.

Rows that are also present in `creates[]` or `updates[]` enter auto-WAC only
because that create/update item requested an auto mode, never because of the
promote item itself.

---

## 🔍 Preview and Response Data

Committed WAC analytics are exposed through:

```text
POST /portfolio/wac
```

Inline batch results use the same `WACPreviewResultItem` schema and additionally
populate `operation`, `index`, and `source_broker_id`. The main fields are:

```python
class WACPreviewResultItem:
    wac: Currency | None
    wac_qualifying_txs: list[WACQualifyingTX]
    wac_missing_pairs: list[WACMissingPairInfo]
    asset_price: Currency | None
    asset_price_stale: BackwardFillInfo | None
    asset_price_missing: bool
    operation: Literal["create", "update"] | None
    index: int | None
    source_broker_id: int | None
```

The pure layer receives `WACInputTX` dataclasses containing the signed quantity,
converted per-unit cost, original currency, request mode, and split-link flag.

---

## 🔗 Related

- 🏗️ **[Transaction Service](service.md)** — Ordered batch stages and caller-owned transaction boundary
- ✂️ **[Split & Promote](split_promote.md)** — Promote's resolved cost-basis contract
- 📖 **[Weighted Average Cost Theory](../../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md)** — Financial methodology
- 🧠 **[FIFO Lot Engine](fifo_lot_engine.md)** — Per-lot alternative to a blended average
