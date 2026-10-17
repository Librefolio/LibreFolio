# 🧬 FIFO Lot Engine

The package `backend/app/services/financial_math/fifo/` contains LibreFolio's **pure, event-sourced FIFO engine** for one asset across many brokers. Unlike [`wac.md`](wac.md), which computes an aggregated **per-position** weighted average cost, `FifoLotEngine` keeps **individual lots** alive through buys, sells, splits, transfers, and adjustments so the "FIFO Lots Analysis" panel can explain **which lot moved where, when, and why**.

The package belongs to the [financial math layer](../financial_math.md) and re-exports nothing: import each name from the module that defines it — the data types (input transactions, events, lots, fragments, closures, economic allocations, `FifoEngineResult`) from `models.py`, `eligible_income_quantity()` from `eligibility.py`, `FifoLotEngine` and `run_fifo_lot_engine()` from `engine.py`.

!!! info "Use this vs WAC"

    `FifoLotEngine` answers **lot-level lifecycle** questions: FIFO matching, realized P&L per lot, custody fragments, transfer transit, split-adjusted quantities, and lot history for charts/modals.

    `portfolio_service.compute_wac_iterative()` plus `services/financial_math/average_cost.py` answer **position-level cost basis** questions: one running WAC per `(broker, asset)` scope, suitable for transaction validation and broker summaries.

---

## 🏗️ Architecture

The engine is intentionally isolated from I/O:

- **No DB queries**
- **No FX conversion**
- **No `quote_base_quantity` scaling**
- **No current-price fetches**
- **No asset price-feed dependency**

It consumes already-loaded transactions plus a few deterministic helpers, then returns a `FifoEngineResult`. FIFO cost matching and realized P&L always come from real transaction prices (`amount / quantity`, cost-basis overrides, and split/transfer replay), never from the asset price feed. Open-position valuation is added later by [`LotsAnalysisService`](lots_analysis_service.md) through the unified `build_asset_price_series()` resolver.

```python
def run_fifo_lot_engine(
    transactions: Sequence[TransactionLike | FifoInputTransaction],
    broker_shorting: dict[int, bool],
    *,
    split_ratios_by_tx_id: dict[int, Decimal] | None = None,
    split_event_ids_by_tx_id: dict[int, int] | None = None,
    reference_price_lookup: ReferencePriceLookup | None = None,
    economic_events: Sequence[EconomicEvent] = (),
    target_currency: str = "",
    replay_until: date | None = None,
) -> FifoEngineResult:
```

### ⚙️ Inputs

| Input | Meaning |
|------|---------|
| `transactions` | Chronological asset transactions for **one asset only**. |
| `broker_shorting` | Per-broker flag controlling whether a `SELL` remainder may open a `SHORT` lot. |
| `split_ratios_by_tx_id` | Split transaction ID → ratio used to synthesize `SPLIT` events. |
| `split_event_ids_by_tx_id` | Split transaction ID → its `SPLIT` `AssetEvent` id, carried by the synthesized event as `asset_event_id`. Yield on Cost passes it; the lots analysis does not. |
| `reference_price_lookup` | Optional pure lookup used by current implementation when `ADJUSTMENT_IN` opens a new LONG lot. The lots analysis passes one that reads the asset's daily marks (see [Reference Price](lots_analysis_service.md#reference-price)); without a lookup, or when it returns `None`, the lot gets `reference_price_source = "unavailable"`. |
| `economic_events` | Asset-linked `DIVIDEND` / `INTEREST` / `FEE` / `TAX` as `EconomicEvent`s, each with its native amount and the target-currency amount its caller resolved; consumed by the [economic allocation stage](#economic-allocation-stage). |
| `target_currency` | The caller's report currency; each `EconomicEvent` also carries its own `target_currency`. `_close_position_piece()` also reads it: a lot or a closing price without a currency counts in it when a closure's currency is compared with its lot's (see [Closure currency](#closure-currency)). |
| `replay_until` | The last day the replay reaches; `None` reaches every event. An event dated after it is neither applied nor returned in `classified_events`: a lots analysis passes its `date_to`, so a transfer whose arriving leg is dated later departs and stays `IN_TRANSIT` (see [Transfers In Transit at the End](lots_analysis_service.md#in-transit-at-date-to)). The pairing still reads both legs. |

### 📤 Output

`FifoEngineResult` contains:

- normalized `classified_events`
- final `lots`
- custody `fragment_intervals`
- FIFO `closures`
- `issues`
- derived `analysis_status` (`COMPLETE`, `DEGRADED`, or `FAILED`)

!!! warning "The engine does not compute market valuation"

    `FifoEngineResult` intentionally exposes **no** market-valuation helper. Market value (`open_quantity / quote_base_quantity * market_price`), target-currency FX, and estimated-at-cost fallback are presentation concerns owned by the lots analysis — `LotsAnalysisService` and its functions in `financial_math/lots/` — not this engine. Keeping them out of the engine avoids a latent ×`quote_base_quantity` valuation bug.

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
| `currency` | Currency of the opening price, captured at open time: the opening row's `currency` for a `BUY` or a short-opening `SELL`; for an `ADJUSTMENT_IN` priced by its `cost_basis_override`, the cost basis's (`cost_basis_currency`, or the row's `currency` when that is empty — an adjustment moves no cash, so its own `currency` is often empty); for one without, the row's `currency`. |
| `open_quantity` | Remaining open quantity after FIFO closures. |
| `realized_quantity` | Quantity already closed. |
| `realized_pnl` | Cumulative native realized P&L from closures, in the lot's currency; `None` from the first closure in another currency on (see [Closure currency](#closure-currency)). |
| `cumulative_proceeds` | Native, in the lot's currency. LONG lots: cumulative closure `proceeds` — a `SELL`'s cash, plus the value an `ADJUSTMENT_OUT` with a cost basis hands over at that cost — `None` from the first closure in another currency on. SHORT lots: the opening proceeds, which closures never change. |
| `reference_unit_price` | Optional reference price the engine resolves for a lot (e.g. when an `ADJUSTMENT_IN` opens a new LONG lot), consumed downstream by `LotsAnalysisService`. |
| `reference_price_source` | `"exact"`, `"fallback"`, `"unavailable"`, or `None`. |

`reference_unit_price` is stored on the market/`quote_base_quantity` axis when the lookup supplies one — resolver marks already live on that axis. When the lot has none — opened by a `BUY` or a short-opening `SELL`, or by an `ADJUSTMENT_IN` with no observation on or before its opening date — `opening_reference_price()` (`financial_math/lots/prices.py`) falls back to `lot.opening_unit_price * quote_base_quantity` before the lots analysis computes `relative_return`; the engine itself does not know `quote_base_quantity`.

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

Single FIFO close operation against one fragment, in native amounts: the lots analysis converts it, each leg at its own date (see [Closure currency](#closure-currency)).

| Field | Meaning |
|------|---------|
| `lot_id` | Closed lot. |
| `transaction_id` | Transaction causing closure. |
| `quantity` | Quantity matched in this closure step. |
| `close_date` | Closure date. |
| `close_reason` | `"SELL"`, `"BUY"`, or `"ADJUSTMENT_OUT"`. |
| `fragment_id` | Exact fragment consumed. |
| `open_unit_price` | Cost carried by the consumed fragment, in the lot's currency. |
| `close_unit_price` | Price the piece closed at, in `close_currency`: the `SELL` / `BUY` unit price; for an `ADJUSTMENT_IN` closing a SHORT, its `cost_basis_override` (0 without one); for an `ADJUSTMENT_OUT`, its `cost_basis_override` — the same for every fragment — or 0 without one. |
| `realized_pnl` | Native realized P&L of the piece, in the lot's currency; `None` when `close_currency` is not the lot's. |
| `proceeds` | `quantity × close_unit_price`, in `close_currency`, on LONG closures — a `SELL`'s cash, or the value an `ADJUSTMENT_OUT` hands over at cost (0 without a cost basis); 0 on every SHORT closure. |
| `close_currency` | Currency of `close_unit_price` and `proceeds`, `None` counting as the report currency: a `SELL`'s or `BUY`'s `currency`; for an `ADJUSTMENT_IN` closing a SHORT, its cost basis's (`cost_basis_currency`, or the row's `currency` when empty) when it carries a `cost_basis_override`, else the row's `currency`; for an `ADJUSTMENT_OUT`, `_handover_currency()`: `cost_basis_currency` when it carries a cost basis, the lot's currency when that is empty or when it carries none. |

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
| `economic_accumulators_by_lot` | Per-lot `gross_income` (signed: a negative income correction lowers it), `allocated_fees`, `allocated_taxes` (positive magnitudes), all in the target currency. |
| `asset_orphan_income` / `asset_orphan_fees` / `asset_orphan_taxes` | Amounts with no eligible lot, kept at asset level. |

Useful helpers on result:

- `analysis_status`: `"FAILED"` if any issue is a non-isolable quantitative-replay error (`fails_the_replay(code)`: a code of `_QUANTITATIVE_FAILURE_CODES` in `models.py`), else `"DEGRADED"` if `issues` is non-empty, else `"COMPLETE"`
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
- positive `ADJUSTMENT` → `ADJUSTMENT_IN`, its `unit_price` the row's `cost_basis_override` (0 without one)
- negative `ADJUSTMENT` → `ADJUSTMENT_OUT`, its `unit_price` the row's `cost_basis_override` (0 without one): every fragment closes at that price, in a currency resolved per fragment when the event is applied (see [Hand-over at cost](#handover-at-cost))
- transaction ID found in `split_ratios_by_tx_id` → `SPLIT`, when its ratio passes `is_valid_split_ratio()`; otherwise the row is skipped: never an `ADJUSTMENT_IN` / `ADJUSTMENT_OUT`, no rescale, no exception (lot MF-D4)
- paired `TRANSFER` legs → synthesized `TRANSFER_DEPART` + `TRANSFER_ARRIVE`

### 📋 Inventory effects

| Event kind | Effect on inventory |
|-----------|---------------------|
| `BUY` | First closes existing `SHORT` fragments on same broker (`close_reason="BUY"`). Any remainder opens new `LONG` lot. |
| `SELL` | Closes `LONG` fragments FIFO on same broker. Any remainder opens new `SHORT` lot only if `broker_shorting[broker_id]` is true; otherwise emits `FIFO_SOURCE_QUANTITY_MISSING`. |
| `ADJUSTMENT_IN` | First closes existing `SHORT` fragments on same broker (`close_reason="BUY"`) at the event's `unit_price` — the row's `cost_basis_override`, 0 without one — in the cost basis's currency when the row carries one (`cost_basis_currency`, else the row's `currency`), else in the row's `currency`. Any remainder opens a new `LONG` lot at that price, in that currency, and resolves its reference price. |
| `ADJUSTMENT_OUT` | Closes `LONG` fragments FIFO on same broker (`close_reason="ADJUSTMENT_OUT"`): with a `cost_basis_override`, every fragment at that per-unit cost, in `cost_basis_currency` (the lot's currency when empty) — the units are handed over at cost; without one, at `close_unit_price = 0` in the lot's currency — a write-off; flagged `hands_over_at_own_cost` (a transfer leg leaving the lots' scope on a day without a price, see [Transfers Across the Scope's Edge](lots_analysis_service.md#scope-edge-transfers)), every fragment at its own FIFO unit cost in the lot's currency — realized 0. If quantity still missing, engine emits issue; it never opens/consumes unsupported SHORT adjustment legs. |
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

Every fragment closes at the one `close_unit_price` the caller passes, in the `close_currency` it passes or in the one the optional per-fragment hook `close_currency_of(fragment)` gives it. `_apply_sell()` and `_apply_buy()` pass the row's `currency`, `_apply_adjustment_in()` the currency of its price; only `_apply_adjustment_out()` passes the hook, `_handover_currency()`, since a fragment it closes without a cost basis, or with one that has no currency, closes in its own lot's currency (see [Hand-over at cost](#handover-at-cost)).

### 🧮 Realized P&L math

- **LONG close**: `matched_quantity * (close_unit_price - fragment.unit_price)`
- **SHORT close**: `matched_quantity * (fragment.unit_price - close_unit_price)`

Both are native, in the lot's currency, and computed only when the closure is in that currency (see [Closure currency](#closure-currency)). `SELL` and `ADJUSTMENT_OUT` — the two closures of LONG inventory — create `proceeds = matched_quantity * close_unit_price`: a sale's cash, or the value an `ADJUSTMENT_OUT` hands over at cost. An `ADJUSTMENT_OUT` without a cost basis closes at 0, in the lot's currency: no proceeds, and it realizes `-matched_quantity * fragment.unit_price` (a write-off). `BUY` and `ADJUSTMENT_IN` close SHORT inventory but do not add proceeds.

### 💱 Closure currency {: #closure-currency }

A closure's two prices can be in two currencies: `open_unit_price` in the lot's (`FifoLot.currency`), `close_unit_price` and `proceeds` in `close_currency` (see the `LotClosure` table). A lot moved to a broker of another currency and sold there closes in the sale's currency; an `ADJUSTMENT_OUT` whose cost basis is in another currency than the lot's closes in the cost basis's.

The engine has no rates, so `_close_position_piece()` computes the native realized P&L only when the two currencies are the same — `None` counts as `target_currency` on both sides, as the lots analysis reads an amount without a currency. Otherwise:

- the closure's `realized_pnl` is `None`;
- the lot's `realized_pnl` is `None` from that closure on, and so is a LONG lot's `cumulative_proceeds`.

The figures in the report currency are the lots analysis's: `convert_closure()` converts each leg at its own date — the lot's side at the lot's opening date, the closing side at the closure date — and never reads the native `realized_pnl` (developer decision 26; see [Closures: each leg at its own date](lots_analysis_service.md#closure-conversion)).

### 📤 Hand-over at cost {: #handover-at-cost }

A negative `ADJUSTMENT` carrying a per-unit `cost_basis_override` hands its units over at that cost (developer decision 47: the principle of a priced `ADJUSTMENT_IN`, in the opposite direction). The Dashboard treats it so: the value handed over, converted at the row's date, leaves the capital baseline, and its difference from the average cost the pool gives up is realized (`DailyStateBuilder._handed_over_value()`, see [WAC & Cost Basis — Portfolio engine](wac.md#portfolio-engine)). The lots agree: every fragment closes at the row's `cost_basis_override` — the event's `unit_price`, **not** the fragment's own `unit_price` — so a fragment of a cheaper lot realizes the difference. Example, in one currency: 10 units bought at 10 and 10 at 20 (average 15); an `ADJUSTMENT_OUT` of 10 at cost 15 closes the first lot at 15 — `realized_pnl = +50`, `proceeds = 150` — and the lots total equals the Dashboard's P&L. With a single lot and a cost equal to the lot's, the realized part is 0.

The cost applies to every fragment, whatever its lot's currency. `_handover_currency(tx, fragment)` gives each closure its `close_currency`: the cost basis's — `tx.cost_basis_currency`, or the lot's currency when empty — or, for a row without a cost basis, the lot's. A cost basis in another currency than the lot's leaves the closure's native `realized_pnl` `None` (see [Closure currency](#closure-currency)); the lots analysis realizes the value handed over, converted at the row's date, against the lot's cost converted at its opening date. With `cost_basis_currency` empty, the Dashboard reads the cost basis in the asset's currency instead (`_handed_over_value()`): the two agree when the lot was opened in the asset's currency.

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

Otherwise engine records `TRANSFER_PAIR_MISSING` and skips pair. The engine sees only the rows it is given: a lots
analysis reads a leg whose partner pairs back from a broker outside its scope before the replay, as an adjustment
(see [Transfers Across the Scope's Edge](lots_analysis_service.md#scope-edge-transfers)), so that leg never reaches
this rule.

### 🛫 Depart {: #depart }

`TRANSFER_DEPART`:

1. refuses current SHORT exposure on source broker (`SHORT_TRANSFER_NOT_SUPPORTED`)
2. extracts source `LONG` fragments FIFO
3. shrinks/closes source broker fragments
4. opens `IN_TRANSIT` fragment when `transit_start < transit_end`
5. stores `_PendingTransferPiece` until arrival

Both issues a departure can record (`SHORT_TRANSFER_NOT_SUPPORTED`, and `FIFO_SOURCE_QUANTITY_MISSING` when the source
broker holds less than the leg moves) name the giving leg, the row to fix: `raw_transaction_ids[0]`, the out leg of the
pair (J-12). The event's own `transaction_id` is the pair's, which may be the receiving leg.

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
  (`eligible_income_quantity(...)`, `eligibility.py`), **scoped to the paying broker** (including quantity that left that
  broker as `IN_TRANSIT`). A BUY made on the income date is therefore not eligible; a lot already closed by
  end of `date - 1` is not either. It is the shared D-1 eligibility seam: transaction-ledger Yield on Cost
  (`backend/app/services/financial_math/yield_on_cost.py`) counts eligible quantity with the same public function.
- weight `w_i = EligibleQty_i / Σ EligibleQty_j`, distributed with a running remainder so the pool total is
  conserved exactly;
- **signed amounts**: a pool sums its `native_amount` / `target_amount` values with their sign, as the Dashboard
  does (`NativeCash.flows()` keeps income signed; developer decision D-MF3): a negative correction lowers the
  income of the lots, and an orphan pool can be negative;
- **no eligible lot** → the whole pool becomes `asset_orphan_income`, with an `ASSET_INCOME_NO_ELIGIBLE_LOTS`
  issue and an audit group tagged `ASSET_INCOME_HOLDINGS`.

### 💸 FEE / TAX

`_allocate_cost_pools()` pools asset-linked cost and matches it to operations with a deterministic ladder
(`_match_cost_operations`), weighting by `target_amount`. Unlike income, a cost pool sums its amounts in
absolute value, as the Dashboard counts fees and taxes:

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

### 📈 Net annualization handoff

The engine returns realized P&L plus economic accumulators; `lot_summary_figures()` (`financial_math/lots/summary.py`), called by `LotsAnalysisService._build_lot_summaries()`, derives `total_pnl`, subtracts allocated FEE/TAX into `net_total_pnl`, computes `net_total_return`, and annualizes **that net figure** over `opening_date → closing_date` (closed lots) or `opening_date → analysis_end` (open lots). The shipped `LotSummarySchema.annualized_return` therefore annualizes `net_total_return`, not gross `total_return`.

---

## ⚠️ Known Constraints and Gotchas

!!! warning "SHORT support is intentionally partial"

    `SELL` may open `SHORT` lots when broker shorting is enabled, and `BUY` / positive adjustment may close them. `TRANSFER_DEPART` on SHORT inventory and `ADJUSTMENT_OUT` against SHORT inventory are currently rejected with `SHORT_TRANSFER_NOT_SUPPORTED` and `SHORT_ADJUSTMENT_NOT_SUPPORTED`.

!!! warning "Reference price behavior is narrower in code than broad system docs may suggest"

    Current implementation calls `_resolve_reference_price()` only in `_apply_adjustment_in()` before opening a remainder LONG lot. Ordinary `BUY` openings pass `reference_resolution=None`, so many lots will have `reference_unit_price is None` unless populated by adjustment flow.

!!! note "Estimated valuation lives outside FIFO"

    The engine has no `ESTIMATED_AT_COST` branch and does not emit `CURRENT_PRICE_ASSUMED_AT_COST`. On a day with no observation on or before it — no quote, no `BUY` or `SELL` — the lots analysis values the open slice of a LONG lot at cost, with no market P&L (see [Estimated-at-Cost Fallback](lots_analysis_service.md#estimated-at-cost-fallback)); a trade-origin mark is a price, flagged `estimated=True` on the price-history line.

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
- 🧮 **[Financial Math Layer](../financial_math.md)** — The layer this package belongs to: rules, package map, guards
- 🧬 **[FIFO Engine Theory](../../../financial-theory/technical-analysis/performance-metrics/fifo-engine/index.md)** — Theoretical mirror of this page: lot lifecycle, matching, splits, transfers in financial terms
- 📖 **[FIFO Lot Analysis Theory](../../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)** — Financial meaning of lot-level FIFO analysis
