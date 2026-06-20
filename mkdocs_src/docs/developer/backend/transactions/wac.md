# WAC & Cost Basis

**WAC (Weighted Average Cost)** — also called *PMC* (Prezzo Medio di Carico) — is LibreFolio's primary cost basis methodology. The implementation lives in `backend/app/services/wac_service.py` and `backend/app/utils/financial_utils.py`.

---

## Architecture: Two Layers

The computation is split into two layers:

```
compute_wac_iterative()          ← async DB layer
    └─ compute_wac_from_txlist() ← pure math layer (no DB, no IO)
```

| Layer | File | Responsibility |
|-------|------|----------------|
| `compute_wac_iterative` | `wac_service.py` | Queries DB, resolves FX, builds input list |
| `compute_wac_from_txlist` | `financial_utils.py` | Pure iterative WAC math, no side effects |

This separation makes the pure math layer fully unit-testable without a database.

---

## `compute_wac_iterative()` — Async Preparation Layer

```python
async def compute_wac_iterative(
    session: AsyncSession,
    broker_id: int,
    asset_id: int,
    as_of_date: date,
    asset_currency: str,
    excluded_tx_ids: list[int] | None = None,
) -> WACPreviewResultItem:
```

Steps performed:

1. **Query** all transactions for `(broker_id, asset_id)` with `date ≤ as_of_date` and `quantity ≠ 0`
2. **Exclude** any IDs in `excluded_tx_ids` (used for WAC preview of a not-yet-saved transaction)
3. **Determine target currency**: inferred from the most frequent acquisition currency; falls back to `asset_currency`
4. **FX conversion**: for acquisitions in a different currency, fetch FX rates and convert to the target currency via `convert_bulk()`
5. **Delegate** to `compute_wac_from_txlist()` for the iterative calculation

---

## WAC Algorithm

The WAC algorithm maintains a running **inventory** of (quantity, average cost):

```
For each transaction in chronological order:
  BUY:       new_wac = (old_qty × old_wac + new_qty × unit_cost) / (old_qty + new_qty)
             inventory += new_qty
  SELL:      inventory -= sold_qty   (WAC does not change on a sell)
  TRANSFER+: treated like BUY using cost_basis_override as unit cost
  TRANSFER-: treated like SELL
  ADJUSTMENT+: treated like BUY
```

The algorithm handles **zero-crossing** (position going to zero): when inventory reaches exactly zero, the WAC is reset to zero. A subsequent acquisition starts a fresh average.

---

## Cost Basis Override (Manual WAC)

Each transaction has two optional fields for manual cost basis override:

| Field | Description |
|-------|-------------|
| `cost_basis_override` | Amount in `cost_basis_currency` representing the total acquisition cost |
| `cost_basis_currency` | Currency of the override (may differ from the transaction currency) |

When `cost_basis_override` is set, the WAC engine uses it instead of computing from the transaction amount. This is essential for:

- **TRANSFER incoming leg** — the receiving broker does not know the original purchase price; the user sets it manually
- **ADJUSTMENT+** — arbitrary quantity adjustments require an explicit cost basis

If `cost_basis_override` is `None` on a BUY, the engine uses `amount` (gross transaction value).

---

## WAC Preview (Real-time)

The transaction form displays a **WAC preview** before the transaction is saved:

```
GET /transactions/wac-preview?broker_id=…&asset_id=…&date=…&…
```

The preview calls `compute_wac_iterative()` with the **pending transaction included** in the input list (injected as an in-memory row, not persisted) to show the projected cost basis after save.

---

## Usage in `execute_batch()`

After creating/updating transactions in a batch, `TransactionService._compute_wac_for_auto_items()` runs WAC for each affected `(broker_id, asset_id)` pair where the transaction has `cost_basis_mode = "auto"`:

```python
await self._compute_wac_for_auto_items(batch_results, session)
```

The result is written back to `transaction.cost_basis_override` so the DB always stores the resolved cost basis (no re-computation on read).

---

## Data Structures

```python
@dataclass
class WACInputTX:
    tx_id: int
    type: str               # "BUY", "SELL", "TRANSFER", "ADJUSTMENT"
    date: date
    quantity: Decimal
    unit_cost_converted: Decimal | None   # in target currency (post FX-conversion)
    original_currency: str
    is_pending: bool        # True for preview-only rows

@dataclass
class WACPreviewResultItem:
    wac: Currency           # Current WAC after all transactions
    wac_qualifying_txs: list[WACQualifyingTX]   # Which transactions affected WAC
    wac_missing_pairs: list[int]                 # IDs of transactions with no cost basis
```

---

## Related

- 🏗️ **[Transaction Service](service.md)** — How WAC is invoked in the batch pipeline
- 📖 **[Weighted Average Cost Theory](../../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md)** — Financial methodology
