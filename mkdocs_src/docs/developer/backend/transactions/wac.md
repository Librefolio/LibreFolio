# ⚖️ WAC & Cost Basis

**WAC (Weighted Average Cost)** — also called *PMC* (Prezzo Medio di Carico) — is LibreFolio's primary blended cost-basis methodology. The shipped implementation lives in `backend/app/services/portfolio_service.py` and `backend/app/utils/financial/wac_utils.py`.

---

## 🏗️ Architecture: Two Layers

The computation is split into two layers:

```text
compute_wac_iterative()          ← async DB/FX/cache layer
    └─ compute_wac_from_txlist() ← pure math layer (no DB, no I/O)
```

| Layer | File | Responsibility |
|-------|------|----------------|
| `compute_wac_iterative` | `portfolio_service.py` | Queries DB, detects split-linked rows, resolves FX, caches by transaction fingerprint, builds input list |
| `compute_wac_from_txlist` | `utils/financial/wac_utils.py` | Pure iterative WAC math, no side effects |

This separation makes the pure math layer fully unit-testable without a database.

---

## ⚙️ `compute_wac_iterative()` — Async Preparation Layer

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

Steps performed:

1. **Query** all transactions for `(broker_id, asset_id)` with `date ≤ as_of_date` and `quantity ≠ 0`
2. **Exclude** any IDs in `excluded_tx_ids` (used by preview/auto-cost flows that must ignore the row currently being resolved)
3. **Detect split-linked ADJUSTMENT rows** through `AssetEvent.type == SPLIT`; these rescale quantity/cost and skip normal add/reduce math.
4. **Determine target currency**: `target_currency_override` if present, otherwise `determine_target_currency()` chooses the latest acquisition currency and falls back to `asset_currency`.
5. **FX conversion**: for acquisitions in a different currency, fetch FX rates and convert to the target currency via `convert_bulk()`.
6. **Delegate** to `compute_wac_from_txlist()` for the iterative calculation.
7. **Return schema**: `WACPreviewResultItem` with current WAC, qualifying rows, FX staleness, and missing FX pairs.

---

## 🧮 WAC Algorithm

The WAC algorithm maintains a running **inventory** of (quantity, average cost):

```text
For each transaction in chronological order:
  BUY:       new_wac = (old_qty × old_wac + new_qty × unit_cost) / (old_qty + new_qty)
             inventory += new_qty
  SELL:      inventory -= sold_qty   (WAC does not change on a sell)
  TRANSFER+: treated like BUY using cost_basis_override as unit cost
  TRANSFER-: treated like SELL
  ADJUSTMENT+: treated like BUY
```

`compute_wac_from_txlist()` sorts by `(date, tx_id)`, then processes same-day additions before reductions to avoid transient negative quantity. The algorithm handles **zero-crossing** (position going to zero): when inventory reaches exactly zero, the WAC is reset to zero. A subsequent acquisition starts a fresh average.

Split-linked rows (`is_split_linked=True`) bypass normal acquisition/reduction logic:

```text
new_qty = qty_pool + tx.quantity
wac = (wac * qty_pool) / new_qty
```

This preserves total cost while redistributing it over post-split quantity.

---

## 🧾 Cost Basis Override (Manual WAC)

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

## 🔍 WAC Preview and Analytics

Committed WAC analytics are exposed through the portfolio router:

```text
POST /portfolio/wac
```

The endpoint calls `compute_wac_iterative()` for each `(broker, asset)` query and builds a point-per-qualifying-transaction series from `wac_qualifying_txs`.

Transaction batch auto-cost-basis uses the same function from `TransactionService._compute_wac_for_auto_items()`. For `cost_basis_mode in ("auto", "auto-detail")`, the service flushes the transaction, computes WAC for the source broker/asset/date, then writes `transaction.cost_basis_override` and `cost_basis_currency`. Split-linked ADJUSTMENT rows are skipped because `wac_utils.compute_wac_from_txlist()` handles split rescaling live.

---

## 💾 Usage in `execute_batch()`

After creating/updating transactions in a batch, `TransactionService._compute_wac_for_auto_items()` runs WAC for each affected `(broker_id, asset_id)` pair where the transaction has `cost_basis_mode = "auto"` or `"auto-detail"`:

```python
await self._compute_wac_for_auto_items(batch_results, session)
```

The result is written back to `transaction.cost_basis_override` so the DB always stores the resolved cost basis (no re-computation on read).

---

## 📦 Data Structures

```python
@dataclass
class WACInputTX:
    tx_id: int | None
    type: str               # "BUY", "SELL", "TRANSFER", "ADJUSTMENT"
    date: date
    quantity: Decimal
    unit_cost_converted: Decimal | None   # in target currency (post FX-conversion)
    original_currency: str
    is_pending: bool        # True for in-memory/non-DB rows when caller supplies them
    cost_basis_mode: str | None
    is_split_linked: bool

@dataclass
class WACPreviewResultItem:
    wac: Currency           # Current WAC after all transactions
    wac_qualifying_txs: list[WACQualifyingTX]   # Which transactions affected WAC
    wac_missing_pairs: list[WACMissingPairInfo]  # Missing FX pairs and dates
```

---

## 🔗 Related

- 🏗️ **[Transaction Service](service.md)** — How WAC is invoked in the batch pipeline
- 📖 **[Weighted Average Cost Theory](../../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md)** — Financial methodology
- 🧠 **[FIFO Lot Engine](fifo_lot_engine.md)** — Per-lot alternative that tracks individual acquisition batches instead of a blended average
