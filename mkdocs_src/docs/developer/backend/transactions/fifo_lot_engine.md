# 🧬 FIFO Lot Engine

`backend/app/services/fifo_lot_engine.py` contains LibreFolio's **pure, event-sourced FIFO engine** for one asset across many brokers. Unlike [`wac.md`](wac.md), which computes an aggregated **per-position** weighted average cost, `FifoLotEngine` keeps **individual lots** alive through buys, sells, splits, transfers, and adjustments so the "FIFO Lots Analysis" panel can explain **which lot moved where, when, and why**.

!!! info "Use this vs WAC"

    `FifoLotEngine` answers **lot-level lifecycle** questions: FIFO matching, realized P&L per lot, custody fragments, transfer transit, split-adjusted quantities, and lot history for charts/modals.

    `wac_service.py` answers **position-level cost basis** questions: one running WAC per `(broker, asset)` scope, suitable for transaction validation and broker summaries.

---

## 🏗️ Architecture

The engine is intentionally isolated from I/O:

- **No DB queries**
- **No FX conversion**
- **No `quote_base_quantity` scaling**
- **No current-price fetches**

It consumes already-loaded transactions plus a few deterministic helpers, then returns a `FifoEngineResult`.

```python
def run_fifo_lot_engine(
    transactions: Sequence[TransactionLike | FifoInputTransaction],
    broker_shorting: dict[int, bool],
    *,
    split_ratios_by_tx_id: dict[int, Decimal] | None = None,
    reference_price_lookup: ReferencePriceLookup | None = None,
) -> FifoEngineResult:
```

### ⚙️ Inputs

| Input | Meaning |
|------|---------|
| `transactions` | Chronological asset transactions for **one asset only**. |
| `broker_shorting` | Per-broker flag controlling whether a `SELL` remainder may open a `SHORT` lot. |
| `split_ratios_by_tx_id` | Split transaction ID → ratio used to synthesize `SPLIT` events. |
| `reference_price_lookup` | Optional pure lookup used by current implementation when `ADJUSTMENT_IN` opens a new LONG lot. |

### 📤 Output

`FifoEngineResult` contains:

- normalized `classified_events`
- final `lots`
- custody `fragment_intervals`
- FIFO `closures`
- `issues`
- derived `analysis_status` (`COMPLETE`, `DEGRADED`, or `FAILED`)

!!! warning "The engine does not compute market valuation"

    `FifoEngineResult` intentionally exposes **no** market-valuation helper. Market value (`open_quantity / quote_base_quantity * market_price`), target-currency FX, and estimated-at-cost fallback are presentation concerns owned by `LotsAnalysisService`, not this engine. Keeping them out of the engine avoids a latent ×`quote_base_quantity` valuation bug.

---

## 🧱 Core Data Structures

### 📦 `FifoLot`

One FIFO lot. Usually opened by a `BUY`, by the remainder of an `ADJUSTMENT_IN`, or by a short-opening `SELL`.

| Field | Meaning |
|------|---------|
| `lot_id` | Stable lot identifier. In practice equals opening transaction ID. |
| `asset_id` | Asset handled by this engine instance. |
| `direction` | `"LONG"` or `"SHORT"`. |
| `opening_transaction_id` | Source transaction that opened lot. |
| `opening_broker_id` | Broker where lot started. |
| `opening_date` | Opening date. |
| `original_quantity` | Original lot quantity, adjusted later by splits. |
| `opening_unit_price` | Per-unit opening cost currently attached to lot. |
| `original_cost` | Original economic cost basis kept invariant across splits/transfers. |
| `currency` | Transaction currency captured at open time. |
| `open_quantity` | Remaining open quantity after FIFO closures. |
| `realized_quantity` | Quantity already closed. |
| `realized_pnl` | Cumulative realized P&L from closures. |
| `cumulative_proceeds` | Cumulative sale proceeds for LONG lots, or opening proceeds for SHORT lots. |
| `reference_unit_price` | Optional reference price the engine resolves for a lot (e.g. when an `ADJUSTMENT_IN` opens a new LONG lot), consumed downstream by `LotsAnalysisService`. |
| `reference_price_source` | `"exact"`, `"fallback"`, `"unavailable"`, or `None`. |

### 🧩 `FragmentInterval`

Custody fragment for one lot. This is what powers Gantt lanes and custody history.

| Field | Meaning |
|------|---------|
| `fragment_id` | Stable fragment key such as origin or transfer-derived IDs. |
| `lot_id` | Owning lot. |
| `direction` | Same lot direction (`"LONG"` / `"SHORT"`). |
| `custody_type` | `"BROKER"` or `"IN_TRANSIT"`. |
| `quantity` | Quantity living in this fragment interval. |
| `unit_price` | Cost per unit carried by this fragment. |
| `start_date` | Inclusive start date. |
| `broker_id` | Broker for broker-custodied fragments. |
| `end_date` | `None` while fragment is active. |
| `source_broker_id` | Transfer source broker for transit fragments. |
| `destination_broker_id` | Transfer destination broker for transit fragments. |

### 🔚 `LotClosure`

Single FIFO close operation against one fragment.

| Field | Meaning |
|------|---------|
| `lot_id` | Closed lot. |
| `transaction_id` | Transaction causing closure. |
| `quantity` | Quantity matched in this closure step. |
| `close_date` | Closure date. |
| `close_reason` | `"SELL"`, `"BUY"`, or `"ADJUSTMENT_OUT"`. |
| `fragment_id` | Exact fragment consumed. |
| `open_unit_price` | Cost carried by consumed fragment. |
| `close_unit_price` | Sell/buy/adjustment close price. |
| `realized_pnl` | Realized P&L for this matched piece. |
| `proceeds` | Non-zero only for LONG `SELL` closures. |

### 📊 `FifoEngineResult`

Returned snapshot of complete run.

| Field | Meaning |
|------|---------|
| `asset_id` | Asset processed by engine. |
| `classified_events` | Normalized event stream after transfer/split classification. |
| `lots` | Final lots sorted by `(opening_date, lot_id)`. |
| `fragment_intervals` | All custody intervals sorted by start date. |
| `closures` | All FIFO closures sorted by close date. |
| `issues` | Data-quality / unsupported-scenario issues. |
| `economic_allocation_groups` | 3-level economic audit (income + FEE/TAX) with source tx, rule, weights, native+target amounts. |
| `economic_accumulators_by_lot` | Per-lot `gross_income`, `allocated_fees`, `allocated_taxes` (target currency, positive magnitudes). |
| `asset_orphan_income` / `asset_orphan_fees` / `asset_orphan_taxes` | Amounts with no eligible lot, kept at asset level. |

Useful helpers on result:

- `analysis_status`: `"FAILED"` if any issue is a non-isolable quantitative-replay error (see `_QUANTITATIVE_FAILURE_CODES`), else `"DEGRADED"` if `issues` is non-empty, else `"COMPLETE"`
- `get_lot_states(lot_id)`: derives `LONG`/`SHORT`, `OPEN`/`PARTIALLY_CLOSED`/`CLOSED`, plus `IN_TRANSIT`, `DISTRIBUTED`, `DEGRADED`
- `active_fragments(...)`: filter live custody fragments

### 🧠 `FifoLotEngine`

Mutable runner around pure input/output contract.

| Member | Purpose |
|------|---------|
| `__init__(...)` | Validates non-empty single-asset input and stores runtime config. |
| `classify_events()` | Normalizes raw transactions into `FifoEvent` objects. |
| `run()` | Applies each event and emits `FifoEngineResult`. |
| `signed_quantity_for_broker()` | Current signed broker exposure from active broker fragments. |

`run()` dispatches strictly by normalized event kind:

```python
for event in events:
    if event.kind == "BUY":
        self._apply_buy(event)
    elif event.kind == "SELL":
        self._apply_sell(event)
    elif event.kind == "ADJUSTMENT_IN":
        self._apply_adjustment_in(event)
    # ... TRANSFER_DEPART / TRANSFER_ARRIVE / SPLIT
```

---

## 🔁 Event Handling

`EventKind` is defined exactly as:

```python
EventKind = Literal[
    "BUY",
    "SELL",
    "ADJUSTMENT_IN",
    "ADJUSTMENT_OUT",
    "SPLIT",
    "TRANSFER_DEPART",
    "TRANSFER_ARRIVE",
]
```

### 🗂️ Classification rules

- `BUY` transaction → `BUY`
- `SELL` transaction → `SELL`
- positive `ADJUSTMENT` → `ADJUSTMENT_IN`
- negative `ADJUSTMENT` → `ADJUSTMENT_OUT`
- transaction ID found in `split_ratios_by_tx_id` → `SPLIT`
- paired `TRANSFER` legs → synthesized `TRANSFER_DEPART` + `TRANSFER_ARRIVE`

### 📋 Inventory effects

| Event kind | Effect on inventory |
|-----------|---------------------|
| `BUY` | First closes existing `SHORT` fragments on same broker (`close_reason="BUY"`). Any remainder opens new `LONG` lot. |
| `SELL` | Closes `LONG` fragments FIFO on same broker. Any remainder opens new `SHORT` lot only if `broker_shorting[broker_id]` is true; otherwise emits `FIFO_SOURCE_QUANTITY_MISSING`. |
| `ADJUSTMENT_IN` | First closes existing `SHORT` fragments with `close_unit_price = 0`. Any remainder opens zero-price `LONG` lot. |
| `ADJUSTMENT_OUT` | Closes `LONG` fragments FIFO with `close_unit_price = 0`. If quantity still missing, engine emits issue; it never opens/consumes unsupported SHORT adjustment legs. |
| `TRANSFER_DEPART` | Extracts `LONG` broker fragments FIFO from source broker, optionally opens `IN_TRANSIT` fragments, records pending transfer pieces, realizes **no P&L**. |
| `TRANSFER_ARRIVE` | Closes matching transit fragments and reopens broker custody at destination with same quantity and unit price. |
| `SPLIT` | Multiplies active fragment quantities by ratio, divides unit prices by ratio, then recomputes lot-level quantities/reference price while preserving cost. |

!!! info "Event ordering on same date"

    `classify_events()` sorts same-day events as `TRANSFER_DEPART` → `TRANSFER_ARRIVE` → `SPLIT` → ordinary transactions. This preserves half-open transfer intervals and lets same-day splits see post-transfer custody state.

---

## ⛏️ FIFO Matching Algorithm

FIFO is enforced by `_broker_fragments()`, which sorts active broker fragments by lot age:

```python
return sorted(
    [fragment for fragment in self._active_fragments.values() if ...],
    key=lambda fragment: (
        self._lots[fragment.lot_id].opening_date,
        fragment.lot_id,
        fragment.start_date,
        fragment.fragment_id,
    ),
)
```

Then `_consume_broker_fragments()` walks oldest fragments first:

1. Select matching broker fragments for one `direction`
2. Take `matched = min(remaining, fragment.quantity)`
3. Call `_close_position_piece(...)`
4. Reduce fragment or close it entirely
5. Continue until requested quantity is satisfied or inventory runs out

### 🧮 Realized P&L math

- **LONG close**: `matched_quantity * (close_unit_price - fragment.unit_price)`
- **SHORT close**: `matched_quantity * (fragment.unit_price - close_unit_price)`

`SELL` creates `proceeds` only when closing LONG inventory. `BUY` closes SHORT inventory but does not add proceeds.

---

## ✂️ Split Handling

`_apply_split()` transforms **active fragments in split scope**, not historical intervals.

### 🎯 Split scope

Current judgement call in code:

- broker fragments match when `fragment.broker_id == split broker`
- in-transit fragments match when `source_broker_id == split broker` **or** `destination_broker_id == split broker`

### 🔄 Ratio transformation

For each impacted fragment:

- `new_quantity = fragment.quantity * ratio`
- `new_unit_price = fragment.unit_price / ratio`
- fragment cost must remain invariant

After fragment transitions, engine updates each impacted lot:

- recompute `open_quantity`
- adjust `original_quantity`
- recompute `opening_unit_price = original_cost / original_quantity`
- scale `reference_unit_price` by `old_open_qty / new_open_qty` when available

!!! warning "Split invariant uses tolerance, not exact equality"

    `_COST_INVARIANT_TOLERANCE = Decimal("0.01")` exists because ratios like `3:1` produce non-terminating decimals under default `Decimal` precision. Sub-cent drift from truncation is tolerated; larger drift raises `AssertionError`.

---

## 🚚 Transfer Handling

Transfers are modeled as **custody moves**, not disposals.

### 🔗 Pair normalization

`classify_events()` accepts only bidirectional `TRANSFER` pairs where:

- both rows are `TRANSFER`
- each row points to other via `related_transaction_id`
- one leg quantity is negative, other positive
- absolute quantities match
- both legs belong to same asset

Otherwise engine records `TRANSFER_PAIR_MISSING` and skips pair.

### 🛫 Depart

`TRANSFER_DEPART`:

1. refuses current SHORT exposure on source broker (`SHORT_TRANSFER_NOT_SUPPORTED`)
2. extracts source `LONG` fragments FIFO
3. shrinks/closes source broker fragments
4. opens `IN_TRANSIT` fragment when `transit_start < transit_end`
5. stores `_PendingTransferPiece` until arrival

### 🛬 Arrive

`TRANSFER_ARRIVE`:

1. pops pending pieces for `pair_id`
2. closes transit fragment on arrival date if one exists
3. opens destination `BROKER` fragment with same `quantity` and `unit_price`

Lot identity stays same across brokers, so frontend can render one lot life with changing custody lanes.

---

## 💸 Economic Allocation Stage

After the replay loop, `run()` calls `_allocate_economics()`. This stage is **read-only** with respect to
inventory: quantities, fragments and closures are **never mutated**. It consumes `economic_events`
(`DIVIDEND` / `INTEREST` / `FEE` / `TAX`, each carrying a `native_amount` and a `target_amount`) and produces
per-lot accumulators, an audit trail, and asset-level orphans.

### 💵 Income (`DIVIDEND` / `INTEREST`)

`_allocate_income_pools()` groups income by pool key
`(broker, date, economic_type, native_currency, target_currency)` and allocates it to eligible lots:

- **Eligibility = D-1**: a lot is eligible if it has open **LONG** quantity as of `date - 1`
  (`_eligible_income_quantity(...)`), **scoped to the paying broker** (including quantity that left that
  broker as `IN_TRANSIT`). A BUY made on the income date is therefore not eligible; a lot already closed by
  end of `date - 1` is not either.
- weight `w_i = EligibleQty_i / Σ EligibleQty_j`, distributed with a running remainder so the pool total is
  conserved exactly;
- **no eligible lot** → the whole pool becomes `asset_orphan_income`, with an `ASSET_INCOME_NO_ELIGIBLE_LOTS`
  issue and an audit group tagged `ASSET_INCOME_HOLDINGS`.

### 💸 FEE / TAX

`_allocate_cost_pools()` pools asset-linked cost and matches it to operations with a deterministic ladder
(`_match_cost_operations`), weighting by `target_amount`:

| Cost | Matching order (first non-empty wins) |
|------|----------------------------------------|
| `FEE` | same-day trades → previous-day trades → holdings fallback → orphan |
| `TAX` | same-day income → same-day trades → previous-day income → previous-day trades → holdings fallback → orphan |

The chosen rule is recorded per group (`SAME_DAY_MIXED_TRADES`, `SAME_DAY_TRADES`, `PREVIOUS_DAY_TRADES`,
`OPEN_LOTS_FALLBACK`, income-linked variants). Allocation to a matched trade **crosses** to the lots that
trade touched (BUY → the opened lot; SELL → the FIFO-consumed lots), so a cost follows the same lots the FIFO
algorithm already selected. A cost with no eligible target becomes `asset_orphan_fees` / `asset_orphan_taxes`.

!!! tip "Per-pool conservation (locked by tests)"

    For every pool: `Σ allocated_to_lots + orphan == converted pool total`. `TestEconomicConservation`
    asserts this invariant, so allocated FEE/TAX/income can never be silently lost or double-counted.

### 🔎 Three-level audit

Each pool emits an `EconomicAllocationGroup` (level 1) → `operation_allocations` (level 2, one per matched
BUY/SELL/income) → `lot_allocations` (level 3, one per lot), all carrying `source_transaction_ids`, `rule`,
`weight`, and both `native_*` and `target_*` amounts. The service maps these to
`economic_allocation_groups` for the response; the frontend does not yet render the provenance (only the
numeric net breakdown).

!!! info "Costs without an asset are out of scope here"

    `FEE` / `TAX` with `asset_id = null` are excluded from `economic_events` entirely — the Portfolio Engine
    accounts for them. Only asset-linked cost reaches this stage.

---

## ⚠️ Known Constraints and Gotchas

!!! warning "SHORT support is intentionally partial"

    `SELL` may open `SHORT` lots when broker shorting is enabled, and `BUY` / positive adjustment may close them. `TRANSFER_DEPART` on SHORT inventory and `ADJUSTMENT_OUT` against SHORT inventory are currently rejected with `SHORT_TRANSFER_NOT_SUPPORTED` and `SHORT_ADJUSTMENT_NOT_SUPPORTED`.

!!! warning "Reference price behavior is narrower in code than broad system docs may suggest"

    Current implementation calls `_resolve_reference_price()` only in `_apply_adjustment_in()` before opening a remainder LONG lot. Ordinary `BUY` openings pass `reference_resolution=None`, so many lots will have `reference_unit_price is None` unless populated by adjustment flow.

!!! info "Issues degrade result instead of aborting run"

    Missing source quantity, broken transfer pairs, and reference-price gaps are recorded in `issues`; the
    replay loop never raises, so the engine still returns best-effort lots/fragments/closures for the rest of
    the input stream. `analysis_status` then becomes `DEGRADED` for isolable (economic) issues, or `FAILED`
    for quantity-topology breakages (oversell, broken transfer, short-not-supported) that cannot be isolated
    because they change which lots later events consume via FIFO order.

---

## 🔗 Related

- 🧮 **[Lots Analysis Service](lots_analysis_service.md)** — Service layer that adds FX, `quote_base_quantity`, income allocation, and DTO building on top of engine output
- ⚖️ **[WAC & Cost Basis](wac.md)** — Complementary per-position cost-basis engine
- 🧬 **[FIFO Engine Theory](../../../financial-theory/technical-analysis/performance-metrics/fifo-engine/index.md)** — Theoretical mirror of this page: lot lifecycle, matching, splits, transfers in financial terms
- 📖 **[FIFO Lot Analysis Theory](../../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)** — Financial meaning of lot-level FIFO analysis
