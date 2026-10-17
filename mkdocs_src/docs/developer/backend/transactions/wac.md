# ⚖️ WAC & Cost Basis

**WAC (Weighted Average Cost)** — also called *PMC* (*Prezzo Medio di
Carico*) — is LibreFolio's blended, per-unit cost-basis method. It has **one
implementation**: `compute_average_costs()` in
`backend/app/services/financial_math/average_cost.py`. The Dashboard's purchase
cost, realized sales and unrealized P&L, the Holdings table's average cost and
Yield on Cost, the WAC lines of the lots analysis, the broker summary, the
transaction preview, the automatic cost basis, `POST /portfolio/wac` and the PAC
planner all read it.

The cost it returns is **historical**: each acquisition costs what was actually
paid, converted into the requested currency at the rate of its own date. It never
moves with today's exchange rate.

```mermaid
flowchart LR
    AC["compute_average_costs()<br/>financial_math/average_cost.py"]
    FX["fx.conversion.convert_bulk()"]
    Engine["PortfolioCalculationEngine<br/>DailyStateBuilder replay"]
    PS["PortfolioService<br/>summary · contribution · holdings"]
    Facade["compute_wac_iterative()<br/>facade"]
    Batch["Batch auto modes"]
    WacApi["POST /portfolio/wac"]
    Pac["PAC planner"]
    Lots["LotsAnalysisService<br/>WAC lines"]
    Broker["BrokerService.get_summary()<br/>holding cost"]

    AC -->|"one batched call"| FX
    PS --> Engine --> AC
    Batch --> Facade
    WacApi --> Facade
    Pac --> Facade
    Facade --> AC
    Lots --> AC
    Broker --> AC
```

!!! info "What it replaced"

    The former WAC helper `compute_wac_from_txlist()`, the portfolio engine's own WAC
    pools (`_buy_unit_cost()`, `_apply_split_rescale()`,
    `_compute_open_cost_basis_inline()`) and `TransactionService.get_cost_basis()`
    no longer exist: `compute_average_costs()` in `financial_math/average_cost.py`
    replaced them all. The engine used to keep each pool in the asset currency and
    convert it at the valuation date, the lots analysis fell back to the unconverted
    cost when a rate was missing, and the broker summary summed BUY amounts. They now
    share the rules below.

---

## 🧱 The Financial Math Layer {: #financial-math-layer }

`compute_average_costs()` and `compute_native_cash()` live in
`backend/app/services/financial_math/`, the one home of LibreFolio's financial
calculations. The layer's rules, its package map and its guards are on their own
page: [Financial Math Layer](../financial_math.md).

| Module | Calculation |
|--------|-------------|
| `average_cost.py` | Average cost of positions: historical cost in the report and asset currencies, the pool after every movement, and the conversions that could not be made |
| `native_cash.py` | Native cash of every broker: balances in their own currencies, their value in the report currency on any day, the exchange result on cash, the period flows by type and position, and the conversions that could not be made |

Each module has one entry point: [`compute_average_costs()`](#compute-average-costs)
and [`compute_native_cash()`](#compute-native-cash).

Their tests are pure — no database, no server, `convert_bulk` replaced on the
module with a double — and live in
`backend/test_scripts/test_services/test_financial_math/` (`test_average_cost.py`,
`test_native_cash.py`), next to the layer's guard:

```bash
./dev.py test services financial-math
```

---

## 🧮 The Average-Cost Function {: #compute-average-costs }

```python
async def compute_average_costs(
    session: Any,
    positions: Sequence[CostPosition],
    *,
    report_currency: str,
    asset_leg: bool = True,
) -> dict[Hashable, AverageCost]:
```

Below, **T** is `report_currency` and **A** is a position's asset currency.

### 📥 Input: plain data

| Type | Fields | Meaning |
|------|--------|---------|
| `CostPosition` | `key`, `asset_currency`, `movements` | One position. `key` is any hashable the caller chooses — `(asset_id, broker_id)`, a broker id, a string; a duplicate key raises `ValueError` |
| `CostMovement` | `movement_id`, `transaction_type`, `date`, `kind`, `quantity`, `cost_amount`, `cost_currency` | One movement of the position's quantity, in the order the caller recorded them |

`CostMovementKind` says what a movement does to the pool:

| Kind | Quantity | Cost |
|------|----------|------|
| `ACQUISITION` | `> 0` | `cost_amount` is the **total actually paid**, in `cost_currency`; `None` means the cost is not known, `0` a free acquisition |
| `REDUCTION` | `< 0` | None: the pool decides what leaves |
| `SPLIT` | `> 0` or `< 0` | None: a split moves quantity, never cost |

`CostMovement` rejects a zero quantity, an acquisition that removes quantity, a
reduction that adds it, a cost on anything but an acquisition, and a cost without
its currency.

### 💱 Conversions

The function converts each acquisition itself, at the acquisition's own date `d`:

| Leg | Rate needed when | Cost of the acquisition |
|-----|------------------|-------------------------|
| Report (T) | paid currency ≠ T | `c_T = paid × r(paid→T, d)`. An amount already in T is taken as it is, so a purchase paid in the report currency never needs a rate |
| Asset (A), only with `asset_leg=True` | A ≠ T and paid currency ≠ A | `c_A = c_T × r(T→A, d)`, the same day's rate. Paid in A: `c_A` is the amount paid. A = T: `c_A = c_T` |

Since `c_A` and `c_T` describe the same purchase at the same day's rate, a
position's exchange-rate effect is zero on the day it is bought.

All the conversions of all the positions go to the FX service in **one**
`convert_bulk(..., raise_on_error=False)` call, each requested once. When every
amount is already in the currency it is needed in, no call is made and `session`
is not used. `convert_bulk` backfills without limit (the latest rate on or before
the date), so a conversion is missing only when the pair has no rate at all on or
before that date, or no route.

!!! warning "A missing rate never becomes a zero"

    The acquisition's quantity still enters the pool, its cost does not: the pool is
    marked incomplete and the pair is reported as a `MissingConversion` with every
    date it was needed on. A report-leg gap is named `FROM/TO` (`GBP/EUR` for a
    purchase paid in pounds, T = EUR) with `leg="report"`; an asset-leg gap is named
    `A/T` (`USD/EUR`) with `leg="asset"`, whichever direction the rate was requested
    in.

### 🔁 Pool rules

The fold keeps, for each position, the quantity `Q` and the total cost `C` on each
leg:

| Movement | Effect on the pool | `CostEffect` |
|----------|--------------------|--------------|
| Same-day ordering | Movements that add quantity first, then those that remove it; within each group the caller's order is kept | — |
| Acquisition with a known cost | `Q += q`, `C += c` | `ADD` |
| Acquisition at zero cost | `Q += q`, `C` unchanged, completeness unchanged | `ADD_ZERO_COST` |
| Acquisition of unknown cost | `Q += q`, `C` unchanged, pool incomplete on both legs; the id is listed in `unknown_cost_movement_ids` | `ADD_UNKNOWN_COST` |
| Acquisition whose rate is missing | `Q += q`, `C` unchanged, pool incomplete on the report leg (and on the asset leg, unless paid in A); pair and date reported | `ADD_MISSING_FX` |
| Reduction | Removes `C × q / Q` on both legs — the **whole** `C` when it empties the pool, so cost is conserved exactly. Quantity beyond the pool is clamped and the id is listed in `oversold_movement_ids` | `REDUCE` |
| Split | `Q` changes, `C` is kept | `SPLIT_RESCALE` |
| Pool emptied | `C = 0` and the pool is complete again: a gap before a full closure does not follow later purchases | — |

### 📤 Output

`compute_average_costs()` returns one `AverageCost` per key:

| Field | Meaning |
|-------|---------|
| `steps` | One `CostStep` per movement: the pool after it, in pool order |
| `missing` | `MissingConversion(pair, dates, leg)` for every conversion that could not be made |
| `unknown_cost_movement_ids` | Acquisitions with no known cost |
| `oversold_movement_ids` | Reductions larger than the pool (no caller surfaces them yet) |
| `quantity`, `cost_report`, `cost_asset`, `report_complete`, `asset_complete`, `unit_cost_report`, `unit_cost_asset`, `has_missing_report_fx` | Properties that read the last step |
| `state_at(day)` | The pool after the last movement dated on or before `day`; `None` before the first one |
| `step_for(movement_id)` | The step of one movement |

| `CostStep` field | Meaning |
|------------------|---------|
| `movement`, `effect` | The movement and what it did to the pool |
| `quantity`, `cost_report`, `cost_asset` | The pool after the movement; `cost_asset` is `None` without the asset leg |
| `cost_report_change`, `cost_asset_change` | Cost added (positive) or removed (negative) by this movement |
| `report_complete`, `asset_complete` | `False` while part of the pool's cost is unknown on that leg |
| `conversion` | `CostConversion` of a converted acquisition: original amount and currency, converted amount, `rate` (converted / original), `rate_date`, `days_back` |
| `unit_cost_report`, `unit_cost_asset`, `cost_report_for(q)`, `cost_asset_for(q)` | Per-unit cost, and the cost of `q` units of the pool |

!!! note "Known part vs. complete cost"

    While a pool is incomplete, `cost_report` holds only its known part: the unknown
    part counts at zero. Aggregates use it as it is — the portfolio's open cost basis
    includes it — while per-position figures (a WAC, an unrealized P&L, a point of a
    lots-analysis WAC line) are withheld rather than shown as a partial average.

### 🔌 Adapters

`cost_movement_from_transaction(tx, *, asset_currency, split_linked, share=1)` maps
a `Transaction` to its movement:

| Transaction | Movement |
|-------------|----------|
| Quantity `None` or `0` (also once scaled by `share`) | `None`: not a movement |
| Split-linked (`ADJUSTMENT` linked to a `SPLIT` `AssetEvent`) | `SPLIT`, whatever its sign |
| Quantity `< 0`, any type | `REDUCTION` |
| `BUY` | `ACQUISITION` costing `abs(amount) × share` in its cash currency `tx.currency` (the asset currency when unset); no amount means a free acquisition |
| Any other type adding quantity (`TRANSFER`, `ADJUSTMENT`) with `cost_basis_override` | `ACQUISITION` costing `cost_basis_override × quantity` in `cost_basis_currency` (the asset currency when unset) |
| The same without `cost_basis_override` | `ACQUISITION` of unknown cost |

`share` — the owner's share of the broker — scales quantity and cost alike.

`determine_target_currency(movements, asset_currency)` returns the currency of the
most recent movement that adds quantity; on a date tie the first one in input
order wins. A split, an acquisition of unknown cost, or no addition at all falls
back to the asset currency.

---

## 💶 The Native-Cash Function {: #compute-native-cash }

```python
async def compute_native_cash(
    session: Any,
    movements: Sequence[CashMovement],
    *,
    report_currency: str,
    rates_until: date_type | None = None,
) -> NativeCash:
```

`financial_math/native_cash.py` is the single reconstruction of every broker's
cash. It keeps each broker's cash in the currencies it was recorded in, and the
engine, the summary and the history endpoints all read it. Below, **T** is
`report_currency`.

### 📥 Movements and Shares

| Name | Meaning |
|------|---------|
| `CashMovement` | One change of a broker's cash, as stored: `movement_id`, `transaction_type`, `date`, `broker_id`, `asset_id` (`None` without a position), `currency`, the signed `amount`, and `share`, the part of the broker the caller counts (default 1). `native` is `amount × share` |
| `cash_movement_from_transaction(tx, *, share=1)` | The movement of a `Transaction`, or `None` when it records no amount or no currency. A zero amount is kept: it belongs to the broker's history but changes no balance |
| `effective_share(role, share_percentage)` | The share a user counts: an `OWNER` its `share_percentage` (`None` counts the whole broker, a zero share is kept), any other role — editor, viewer — the whole broker |
| `rates_until` | The last day the balances are valued on; `None` means each currency's last movement |

### 💱 One Conversion Call

All the conversions go to the FX service in **one**
`convert_bulk(..., raise_on_error=False)` call:

- every non-zero movement in a currency other than T, at its own date — for the flows;
- one unit of each foreign currency on every day from its first movement through
  `rates_until` — for the balances. The days start on `EARLIEST_RANGE_START`
  (1 January 1900, `utils/datetime_utils.py`) when the first movement is earlier: a
  movement stored centuries back would otherwise ask one rate per day since
  (R13-SEC8). Before the floor only the movements' own days are asked, so a balance
  counted there still has a rate on or before every later day.

When every non-zero amount is already in T, no call is made and `session` is not
used: cash held only in the report currency never needs a rate.

| Rule | Effect |
|------|--------|
| Latest rate | A balance is valued at the latest rate on or before the day, so foreign cash is revalued every day |
| Zero amount | Changes no figure and never needs a rate |
| Share | Scales every amount |
| Missing conversion | Never becomes a zero: the movement stays out of values and flows, its own-currency balance still counts it, and its pair is reported as `MissingCashConversion(pair, dates)` (`USD/EUR` for dollars with T = EUR) with every date it was needed on |

!!! warning "`rates_until` must reach every movement and every valued day"

    The engine passes the run's end date, on or after every movement it reads. The
    function does not check it: a day after `rates_until` is valued at the last rate
    requested, and `value_at()` raises `ValueError` when a non-zero foreign balance
    has no rate at all on or before the day.

### 📤 The `NativeCash` Result

A movement is **counted** when its amount is not zero and its conversion was made.
Windows are `(date_from, date_to]`; `None` leaves that side open.

| Member | Returns |
|--------|---------|
| `value_at(day)` | Each broker's cash on `day` in T, every foreign balance at that day's rate. Only brokers with a counted movement on or before `day` appear |
| `balances(as_of=None)` | Each broker's balance in each currency, in that currency; zero and unconverted movements included |
| `flows(date_from, date_to)` | `CashFlows`, the window's movements at their own dates: `signed_by_type`, `absolute_by_type`, `income_by_position` and `costs_by_position` keyed `(broker_id, asset_id)`, `unallocated_income` and `unallocated_costs` by broker. Income (DIVIDEND, INTEREST) keeps its sign, costs (FEE, TAX) are absolute |
| `sums_by_date(date_from, date_to, transaction_types)` | Counted movements summed by date and type, dates ascending |
| `missing_conversions(date_from, date_to, transaction_types)` | One `MissingCashConversion` per pair |
| `exchange_results(date_from, date_to)` | Each foreign-cash broker's exchange result on cash, ascending by broker, zeros included; `{}` for an empty window |
| `rate_change_days(date_from, date_to)` | The days in `[date_from, date_to]` on which the rate of a held foreign currency changes; a currency's first rate counts. Found by `change_days()`, below |
| `foreign_cash_broker_ids` | Brokers with a counted movement outside T |

`rate_change_days()` takes its days from the module's pure function
`change_days(read, currencies, days)`, the one home of «the day a rate changes», which the
portfolio engine calls too, each with its own reading: the native cash the last rate known on or
before the day, on the calendar of its rate points, and the engine the exact day's rate in
`fx_rate_map`, on every replayed day (see
[The Days the Engine Recomputes](../financial_math.md#recomputed-days)).

The exchange result is what the rates did to the cash a broker held: the change in
value of its foreign balances, each at its day's rate, less the window's foreign
movements converted at their own dates.

```text
result(b) = Σ over c ≠ T of [ N(b, c, t1) × r(c, t1) − N(b, c, t0) × r(c, t0) ]
          − Σ over b's counted movements m in (t0, t1], currency ≠ T, of converted(m) × share(m)
```

`CONVERSION_DUST` (`1e-9`): the same cash converted twice — at its movement's date
and through the day's unit rate — can differ in the last of `Decimal`'s 28 digits.
`exchange_results()` returns the difference whole; a caller showing an exchange
result leaves out anything smaller.

### 🔌 Native-Cash Callers

| Caller | Use |
|--------|-----|
| `PortfolioCalculationEngine.calculate()` (`financial_math/portfolio/engine.py`, step 10c) | Builds it once per run from the classified transactions dated up to the run's end, each at its broker's `effective_share()`, with `rates_until` = the run's end; hands it to `DailyStateBuilder(native_cash=...)` and exposes it as `PortfolioCalculationResult.native_cash` |
| `DailyStateBuilder._revalue_foreign_cash()` (`financial_math/portfolio/daily_state.py`) | On every `rate_change_days()` day of the replay, those before `date_from` included, after the day's cash movements and before its transactions: books `value_at(day)` minus the replayed cash of each `foreign_cash_broker_ids` broker into that broker's cash and `R_b` (a negative `R_b` drains into `K_b`, like a FEE), never into the capital baseline → [Portfolio Engine — §6 Three-Pool Cash Model](../../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/index.md#6-three-pool-cash-model-per-broker-k_b-r_b-w) |
| `DailyStateBuilder._valuation_rate_change_days()` (`financial_math/portfolio/daily_state.py`) | `change_days()` with `_read_rate()`, the exact day's rate in `fx_rate_map`: for the non-report currencies of the assets and their quotes on every replayed day, and for the departure currency of cash in transit on the days of its transit. The days it returns are dirty days of the replay, like the `rate_change_days()` days → [The Days the Engine Recomputes](../financial_math.md#recomputed-days) |
| `PortfolioService.get_summary()` | Reads the engine's: broker card cash = `value_at(end)`, per-currency chips = `balances(end)`, summed over the cards for the headline chips; period and lifetime deposits, withdrawals, income, fees and taxes = `flows()`; missing pairs = `missing_conversions(None, end)`. The headline cash is the engine's, revalued on the same days, so it matches the sum of the cards |
| `PortfolioService._signed_transaction_sums_by_date()`, behind `get_income_history()`, `get_cost_history()` and `get_deposit_history()` | `sums_by_date()` and `missing_conversions()`; the report passes the engine's native cash, a standalone call builds its own with `rates_until` = `date_to`, or today |
| `PortfolioService.get_positions_contribution()` | Reads the engine's: period income and costs by position and broker = `flows()`. When the period's Other can be computed, one **FX on cash** row per broker = `exchange_results(date_from, end)`, in broker access order, and the reconciliation residual drops by the same amount. With foreign cash in scope, neither a row nor the residual is shown below `CONVERSION_DUST`; a scope with cash only in T shows any non-zero residual |

The tests are in
`backend/test_scripts/test_services/test_financial_math/test_native_cash.py`, run
with the layer's command:

```bash
./dev.py test services financial-math
```

---

## 🔌 Average-Cost Callers {: #callers }

| Caller | Positions | `report_currency` | `asset_leg` |
|--------|-----------|-------------------|-------------|
| `PortfolioCalculationEngine.calculate()` (`financial_math/portfolio/engine.py`) | `build_cost_positions()`: one per `(asset_id, broker_id)` | The report's target currency | `True` |
| `compute_wac_iterative()` (`portfolio_service.py`) | The one `(broker, asset)` asked for | The override, or `determine_target_currency()` | `False` |
| `LotsAnalysisService` (`lots_analysis_service.py`) | One per broker, plus `"__all__"` pooling every broker in scope | The analysis `target_currency` | `False` |
| `BrokerService.get_summary()` (`brokers/summary.py`) | One per asset held at the broker | The asset's own currency, one call per currency | `False` |

### ⚙️ Portfolio engine {: #portfolio-engine }

1. `build_cost_positions(classified_txs, asset_currencies, target_currency, split_linked_tx_ids, date_to)`
   (`financial_math/portfolio/derived_views.py`)
   turns the classified transactions into one `CostPosition` per
   `(asset_id, broker_id)`: quantity and cost scaled by the owner's share, in
   classification order (date, then id) — the order the replay visits them —
   and without the transactions after `date_to`.
2. `PortfolioCalculationEngine.calculate()` makes **one** `compute_average_costs()`
   call for the whole scope before the daily replay and hands the result to
   `DailyStateBuilder(average_costs=...)`.
3. `DailyStateBuilder` (`financial_math/portfolio/daily_state.py`) replays each
   position's steps through `_next_cost_step()`.
   The step must belong to the transaction being replayed (same movement id and
   date): a mismatch is a bug, never data, and raises `RuntimeError`. No cost is
   converted in the daily loop, and `_preload_fx_rates()` (`financial_math/portfolio/engine.py`)
   no longer asks for acquisition-date rates. It does ask, for each priced outgoing
   `ADJUSTMENT` (negative quantity, `cost_basis_override` set), the rate of its
   `cost_basis_currency` — the asset's currency when empty — on the row's own date,
   before the period too: the value the row hands over is a movement, converted at
   its date (below).

What the replay takes from the steps:

| Output | Source |
|--------|--------|
| `DailyPortfolioState.open_cost_basis` | Σ `cost_report_for(qty)` over the held positions: historical cost in the target currency (its known part) |
| `DailyPositionState` | `wac` per unit in the target currency (`None` while the cost is incomplete), `wac_currency` (the target currency), `cost_basis`, `unrealized_pnl` (`None` without a market value or with an incomplete cost; 0 for a position valued at cost), `asset_currency`, `wac_asset`, `cost_complete` |
| Value of a held position the price resolver cannot mark (`ESTIMATED_AT_COST`) | `cost_report_for(qty)` of a pool complete on the report leg; an incomplete pool leaves it `MISSING` (see [Price Resolver](price_resolver.md#valued-at-cost)) |
| `PortfolioCalculationResult.realized_sales` | One `RealizedSale` per disposal (`_realized_disposal()`): a SELL, its `proceeds` the amount converted at the sale date (`_realized_sale()`), or a priced outgoing `ADJUSTMENT` (`_is_capital_adjustment()`), its `proceeds` the value it hands over (`_handed_over_value()`: `abs(quantity) × cost_basis_override`, in `cost_basis_currency` or the asset's currency, converted at the row's date). Both are scaled by the share and `None` when they cannot be converted; `cost` = the historical cost the step removed, `cost_complete` = completeness of the pool before the disposal |
| Capital baseline of priced in-kind `ADJUSTMENT`s | In: the cost the step added (`ADD` steps only). Out: the value the row hands over (`_handed_over_value()`), or the cost the step removed when that value cannot be converted (the pair is in `missing_fx` with the row's date); the difference from the cost removed is the row's `RealizedSale`. An outgoing `ADJUSTMENT` without a cost basis moves no capital and has no `RealizedSale` |
| Capital of a `TRANSFER` of a security with no price at all | An orphan leg: the cost its own step moved (`cost_report_change`), in or out of the scope's capital — the book cost both ways, like an incoming in-kind `ADJUSTMENT` (an outgoing one takes out the value it hands over instead). An unknown cost counts as zero, the pool's convention, so a leg out of a pool of incomplete cost (a `MISSING` holding) still takes its known cost out, and nothing is left in capital once the units are gone. An internal pair between two brokers: the per-broker flow is the cost the receiving leg's step added (`_movement_cost_step()` on the receiving leg), rescaled from the receiver's share to the sender's, whether or not the receiver's pool is complete; an arrival of unknown cost adds 0, so there is no flow |
| `DailyPortfolioState.unrealized_by_currency` | `UnrealizedSplit(asset, fx, unsplit)` per asset currency, see below |
| `EngineEndState.wac_pool_qty` / `wac_pool_cost` | Quantity and historical cost of the last replayed step |
| `PortfolioCalculationResult.average_costs` | The whole `AverageCost` map, for the services that read it |

In-transit assets with a frozen cost (`cost_basis_amount`) are converted at the
**arrival date**, as the destination pool books them, instead of every day of the
transit.

#### 💱 Unrealized split by currency {: #unrealized-split }

For the positions in assets priced in currency A, reported in T, with `r(t)` the
A→T rate of the day and `C_A`, `C_T` their historical cost in A and in T, every
daily state holds in `unrealized_by_currency[A]` the sum over those positions of:

| Part | Formula | Meaning |
|------|---------|---------|
| `asset` | `MV − C_A × r(t)` | What the assets did in their own currency, at the day's rate |
| `fx` | `C_A × r(t) − C_T` | What the exchange rate did to their cost |
| `unsplit` | `MV − C_T` | Positions that cannot be split that day: no market value, no rate, or a cost incomplete on either leg |

For A = T the whole `MV − C_T` goes to `asset`: `fx` is always zero. A position valued at its
book cost (`ESTIMATED_AT_COST`, no price at all) adds to no part
(`_add_unrealized_part(..., at_cost=True)`): its `MV − C_T` is zero by construction, and
splitting it would invent an asset part and an exchange-rate part of opposite sign; its currency
keeps its entry. Summed over the currencies, the parts equal `market_value − open_cost_basis`
exactly.

`PortfolioService` turns two of these states into
`PortfolioSummary.period_unrealized_breakdown` (`_unrealized_breakdown_rows()`):
`UnrealizedBreakdownRow(kind, asset_currency, period_delta)` holds the change
between the last state on or before `date_from` (zero without one) and the state
at the end date — the same two states as `period_unrealized_gain_loss_delta`, so
the rows add up to it exactly. Order: an `asset` row for every currency (the report
currency first, then alphabetical), an `fx` row for every other currency, then an
`unsplit` row only for a currency whose unsplit part is non-zero at either
boundary. The list is empty when there is no unrealized delta.

#### 🩺 Movement-level FX channel

`PortfolioCalculationResult.missing_fx` (`{"FROM/TO": {dates}}`) collects every
conversion a movement needed and could not get, at the date the movement happened:
the average costs' `missing` (both legs), cash amounts, external cash flows, the
value a priced outgoing `ADJUSTMENT` hands over and the in-transit asset cost. Valuation failures stay per day in
`DailyPortfolioState.missing_fx_pairs`. The
[Data Quality Banner](../../frontend/data-quality-banner.md#where-missing-fx-pairs-come-from)
page explains how both reach the Dashboard.

### 📊 PortfolioService

- **Realized of the period.** `_period_realized_sales()` keeps the engine's
  `realized_sales` — SELLs and priced outgoing `ADJUSTMENT`s — dated in
  `(date_from, date_to]` whose proceeds and cost are both known; realized =
  Σ (proceeds − cost). A disposal left out is reported instead (its pair, or the
  cost basis its pool lacks). There is no per-sale WAC query.
- **Period-boundary values** (positions contribution). Each row reads the engine's
  `position_states_start` / `position_states_end`: the end cost only when `cost_complete`,
  and `unrealized_pnl` is `None` while the cost is incomplete, so no partial cost enters an
  unrealized figure.
- **Holdings.** `wac_per_unit` is the historical WAC already in the report currency
  (`None` while incomplete). It is also the Yield on Cost denominator, which
  therefore needs no conversion at the end date.
- **Data quality.** `_engine_missing_fx_pairs()` and `_missing_cost_basis_assets()`
  feed `build_data_quality_report()` (`financial_math/portfolio/data_quality.py`):
  missing pairs and `MISSING_COST_BASIS`.

### 🔬 Lots analysis

`LotsAnalysisService` draws its broker and cumulative WAC lines from one
`compute_average_costs()` call and reports their gaps (missing rates, unknown costs); see
[Lots Analysis Service — WAC lines](lots_analysis_service.md#wac-lines).

### 🏦 Broker summary {: #broker-summary }

`GET /brokers/{broker_id}/summary` (`BrokerService.get_summary()`):

- `as_of`, a query parameter, is the day the summary describes: the user's day,
  which the broker page sends as `todayIso()`; when it is omitted, `date.today()`
  on the server. Cash and quantities ([Balance Queries](service.md#balance-queries))
  and the holdings' average cost (`_holding_average_costs()` filters
  `date <= as_of`) count only the transactions dated up to `as_of`: one dated
  later counts in none of them (W-B5). The price is not cut: it stays the latest
  close in `price_history`.
- `_holding_average_costs()` loads the broker's quantity-moving transactions of
  the held assets, ordered by date then id, detects the split-linked adjustments,
  and calls `compute_average_costs()` once per asset currency, with that currency
  as report currency.
- `BRAssetHolding.total_cost` is the historical cost of the quantity held, **in the
  asset currency**: each purchase converted at its own date, sales removing their
  share of the average. It is `None` when part of it is unknown (a missing rate, or
  a transfer without cost basis); `average_cost_per_unit` and the unrealized P&L
  are then `None` too.
- `BRSummary.missing_fx_pairs` lists the pairs the holdings' cost needed, with the
  purchase dates.

---

## 🩺 Diagnostics {: #diagnostics }

What each caller does when part of a cost is missing:

| Gap | Engine and Dashboard | Facade | Lots analysis | Broker summary |
|-----|----------------------|--------|---------------|----------------|
| No rate on or before a purchase date | The position's `wac` and `unrealized_pnl` are `None`, the open cost basis keeps the known part; the pair and dates reach `summary.missing_fx_pairs` and a `MISSING_FX_MARKET` / `MISSING_FX_RATES` issue | `wac=None` and `wac_missing_pairs`; in a batch, a `wacFxUnavailable` issue | No point on the days the pool is incomplete; the pair reaches `data_quality`, status `DEGRADED` | `total_cost=None`; the pair is in `missing_fx_pairs` |
| `TRANSFER` / `ADJUSTMENT` adding quantity without `cost_basis_override` | `MISSING_COST_BASIS` warning; the position's `wac` and `unrealized_pnl` are `None`; the units count at zero in the open cost basis | Counted at zero: an `add_zero_cost` row dilutes the WAC | No point while the pool is incomplete; `MISSING_COST_BASIS` for the analysed asset, status `DEGRADED` | `total_cost=None` |

A reduction larger than the pool is clamped everywhere: the pool empties and the
movement id is listed in `oversold_movement_ids`.

---

## 🧾 The WAC Facade {: #wac-facade }

`compute_wac_iterative()` in `backend/app/services/portfolio_service.py` serves
the callers that need one position's WAC with its qualifying rows. Its contract did
not change with the single implementation.

```python
async def compute_wac_iterative(
    session: AsyncSession,
    broker_id: int,
    asset_id: int,
    as_of_date: date,
    asset_currency: str,
    excluded_tx_ids: list[int] | None = None,
    target_currency_override: str | None = None,
    use_cache: bool = True,
) -> WACPreviewResultItem:
```

The facade:

1. queries the non-zero-quantity transactions of the broker and asset through
   `as_of_date`;
2. identifies the `ADJUSTMENT` rows linked to a `SPLIT` `AssetEvent`;
3. fingerprints the rows (id and `updated_at`) and the split linkage for the WAC
   cache, keyed together with the broker, asset, date, asset currency, override and
   excluded ids; `use_cache=False` bypasses the cache;
4. drops the excluded ids and sorts the rest by `(date, id)`; with no rows left it
   returns a zero WAC in the asset currency;
5. maps the rows with `cost_movement_from_transaction()`;
6. chooses the target currency: `target_currency_override`, or
   `determine_target_currency()` — the currency of the last acquisition;
7. calls `compute_average_costs()` for that one position, with
   `asset_leg=False`;
8. returns `wac=None`, no qualifying rows and the missing pairs with their dates
   when a report-leg conversion is missing — that result is not cached;
9. otherwise returns the WAC (`unit_cost_report`, in the target currency, rounded to what
   `Transaction.cost_basis_override` keeps with `round_computed_value()` — C-97 decision D6, MF-W56: the
   preview is frozen into a manual cost and the auto cost is written on the row, so a periodic quotient must
   fit the column; the average itself stays exact in `average_cost`) and one `WACQualifyingTX` per step, and
   caches the result.

Each step becomes a qualifying row:

| `CostEffect` | `WACQualifyingTX.effect` | `unit_cost` |
|--------------|--------------------------|-------------|
| `ADD` | `add` | Cost added ÷ quantity, in the target currency |
| `ADD_ZERO_COST` | `add_zero_cost` | `0` |
| `ADD_UNKNOWN_COST` | `add_zero_cost` | `0`: the preview counts an unknown cost at zero |
| `REDUCE` | `reduce` | The running WAC before the reduction |
| `SPLIT_RESCALE` | `split_rescale` | The running WAC after the split |

`running_wac` is the WAC after the step. A converted acquisition also carries its
provenance: `fx_info` (rate date and days back), `original_unit_cost`,
`original_currency` and `fx_rate_used`.

| Caller | `as_of_date` | Target currency |
|--------|--------------|-----------------|
| Batch auto modes (`TransactionService._compute_wac_for_auto_items()`) | The row's date; the partner's date for the receiving side of a `TRANSFER` | The `cost_basis_override.code` sent as a hint, or the last acquisition's currency |
| `POST /portfolio/wac` (`portfolio_api.py`) | The query's end date, or today | The last acquisition's currency |
| PAC planner (`portfolio_allocation_source.py`) | The planner's date | The planner's target currency, as override, with `use_cache=False` |

!!! note "Two target-currency rules"

    The documented decision *WAC target currency = last acquisition's currency*
    (devWiki: `decisions/wac-target-currency-last-acquisition`) still holds for the
    transaction preview, the automatic cost basis and `POST /portfolio/wac`. The
    Dashboard and everything the portfolio engine produces use the report currency.

---

## 🧾 Persisted Cost Basis

`transactions.cost_basis_override` is a **per-unit** amount, not a total
acquisition cost. Its currency is stored in `cost_basis_currency`; the two values
are written and cleared together by the transaction flows.

| Field | Meaning |
|-------|---------|
| `cost_basis_override` | Frozen WAC for one unit |
| `cost_basis_currency` | ISO currency code for that per-unit amount |

A `BUY` costs the absolute cash amount, in its cash currency. A `TRANSFER` or
`ADJUSTMENT` adding quantity costs `cost_basis_override × quantity`, in
`cost_basis_currency`, converted at its own date like any other acquisition. A
`BUY` without amount is a free acquisition; a `TRANSFER` or `ADJUSTMENT` without
override has an unknown cost (see [Diagnostics](#diagnostics)). Which rows need an
override is read from `TX_TYPE_METADATA`, the table `GET /transactions/types`
serves: `TransactionService._requires_cost_basis()` calls `cost_basis_required()`
(`backend/app/schemas/transactions/type_metadata.py`), which takes the type's
`cost_basis_pair` when it has one — `[1]` for a positive quantity, the receiving
side, `[0]` otherwise — and its `cost_basis_mode` if not; `required_qty_pos` asks
for an override when the quantity is positive.

Rule 12 of `validate_transaction_business_rules()`
(`backend/app/schemas/transactions/transactions.py`) reads the same table through
`cost_basis_allowed()`: a row sent with a `cost_basis_mode` is refused
(`costBasisModeIncompatible`) when the rule of its side — picked at call time by
`_cost_basis_rule()`, shared with `cost_basis_required()` — is `forbidden`, or
`required_qty_pos` without a positive quantity. It is the test the frontend makes
before sending a cost basis (`cbAllowed` in
`frontend/src/lib/features/transactions/txPayloadHelpers.ts`), and with today's
table it admits exactly the rows that need an override: a `TRANSFER` or
`ADJUSTMENT` adding quantity.

The batch rejects such a row without an override (`costBasisRequired`) when it is
created or made the receiving side of a promoted pair (see
[Promote boundary](#promote-boundary)), and when an update changes its type,
quantity, cost basis or its asset event link, or names a `cost_basis_mode`; a row
in Auto is given the computed WAC instead. The update check,
`_check_update_cost_basis()`, compares the row's `cost_fields()` — type, quantity,
`cost_basis_override`, `cost_basis_currency`, `asset_event_id` — with
`stored_cost_fields`, which `_load_existing_transactions()` takes when the batch
loads its rows. So an update of only the notes, tags or date of a row stored
without an override passes, and the row keeps its unknown cost. An acquisition of
unknown cost therefore comes from:

- data the batch never checked: written outside it, or promoted by an earlier
  version, which did not check promoted pairs; or
- an `ADJUSTMENT` linked to a `SPLIT` event that is later retyped. Auto stores no
  cost on a split-linked row (see
  [Split-linked adjustment skip](#split-linked-adjustment-skip)), so once the
  event is no longer a `SPLIT` its units have an unknown cost
  (`test_forward_split_relabelled_as_price_adjustment_becomes_an_unknown_cost_acquisition`
  in `backend/test_scripts/test_api/test_portfolio_wac.py`).

**An explicit `null` in an update** (decision P5, coordinator reading B, 16/10).
An update that leaves out `cost_basis_override` changes nothing. One that sends it
as `null` removes the cost basis stored on the row — `cost_basis_override` and
`cost_basis_currency` together — where the row, with the update's type and
quantity applied, takes one (`cost_basis_allowed()`): `_apply_update_values()`
(`batch_edits.py`) tells the `null` from a missing key by `model_fields_set`.
Where a cost basis is required — on today's table, every side that takes one: a
received `TRANSFER`, an `ADJUSTMENT` adding quantity — the removal changes the
row's `cost_fields()`, so the update check above refuses it with
`costBasisRequired` (operation `update`, `field` `cost_basis_override`), and the
stored cost stays. Elsewhere the `null` is ignored, so the giving leg of a split
`TRANSFER` keeps the cost decision 47 gives it (see
[Split & Promote](split_promote.md#transfer-giving-leg)). It is ignored too when
the update names `cost_basis_mode` `auto` or `auto-detail`, which compute their
own (see [Inline Batch Auto Modes](#inline-batch-auto-modes)): the frontend sends a
`null` with an Auto row that has no currency hint yet (`buildUpdateDiff()` in
`frontend/src/lib/features/transactions/txPayloadHelpers.ts`). Tests:
`./dev.py test services transaction-cost-basis-rule`
(`TestDecisionP5AnExplicitNullEmptiesTheCost`).

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

- `_auto_cost_source()` chooses the pool to average. The receiving side of a
  `TRANSFER` — a `TRANSFER` row with `related_transaction_id` — averages its
  partner's broker as of the partner's date, when the units left, leaving out the
  partner's outgoing leg and the row itself;
- any other row — an incoming `ADJUSTMENT` — averages its own broker as of its
  own date, leaving itself out;
- `_auto_cost()` averages that pool with `compute_wac_iterative()`, once it has
  checked that every row of it can be read (see [Unreadable pool](#unreadable-pool));
- a supplied `cost_basis_override.code` acts as the target-currency hint; and
- a calculated `wac` is written to `cost_basis_override` and
  `cost_basis_currency` on the staged ORM row.

`related_transaction_id` is in place before the WAC step whatever the origin of
the pair: `resolve_create_links()` sets it for a pair created in the same batch,
`apply_promotes()` for a pair formed by a promote, and a saved pair being updated
brings it from the database (`TXUpdateItem` has no `link_uuid`). Since
`cost_basis_mode` is accepted only on a `TRANSFER` or `ADJUSTMENT` adding quantity
(`costBasisModeIncompatible` otherwise; see
[Persisted Cost Basis](#persisted-cost-basis)), a `TRANSFER` in Auto is always the
receiving side.

Reading the source pool as it was when the units left keeps their cost: a
transfer of the whole position keeps the source's average, where counting the
outgoing leg would empty the pool and give 0; a partial transfer gets the same
value with or without that leg, since a reduction does not move the unit cost;
and purchases made on the source broker while the units are in transit stay out.

Under the same condition, after the Auto rows, `compute_wac_and_fx_issues()` prices
the giving leg of each `TRANSFER` pair the batch splits (`context.handover_rows`):
`_handover_cost()` averages the leg's own broker, up to its date, without the leg,
and `_write_auto_cost()` writes the result, unless an update of the batch gives the
leg a `cost_basis_override` (decision 47; see
[Split & Promote](split_promote.md#transfer-giving-leg)). A broker deletion writes
the same cost on a giving leg it leaves without its partner (see
[Broker Deletion](service.md#broker-deletion)).

The create stage has already flushed new rows for generated IDs, and all of this
work remains in the caller's session. Neither the WAC helper nor the surrounding
batch stages commit.

### 🧬 Split-linked adjustment skip {: #split-linked-adjustment-skip }

If the selected row references an `AssetEvent` of type `SPLIT`, auto mode clears
both stored cost-basis fields and emits a batch WAC result with `wac=None` and no
missing pairs. The average cost rescales the live pool when it meets the
split-linked adjustment; storing the pre-split WAC would double-count the economic
cost.

### 💱 Missing FX behavior

If `compute_wac_iterative()` returns no WAC and reports missing FX pairs, the
batch stage appends a `TXValidationIssue` with:

- code `wacFxUnavailable`;
- the originating create/update operation and index or, for the giving leg of a
  split `TRANSFER` pair, operation `split`, the split's index and `ref_id` that
  leg;
- field `cost_basis_override`; and
- pair names plus required dates in `params`.

The response may still include `wac_results`, but the issue makes
`committed=False`; the route that owns the session then rolls back.

### 🚫 Unreadable pool {: #unreadable-pool }

Since W-B58, a stored decimal that is no number — a text, or a REAL ±inf that an
older version or another tool left — reads back as `None` instead of raising
(`RealDecimal`, see [Decimal Columns](../../architecture/database/index.md#decimal-columns)).
The facade does not stop on such a row: `cost_movement_from_transaction()` skips a
row whose quantity reads `None`, takes a `BUY` whose amount reads `None` for a free
purchase, and an acquisition whose cost basis reads `None` for one of unknown cost,
counted at zero. An Auto cost averaged from that pool would be written on the row,
wrong for good.

So `_auto_cost()` (`auto_cost.py`, W-B69) first counts the unreadable rows of the
pool with `_unreadable_pool_rows()`: the rows `compute_wac_iterative()` loads — same
broker and asset, a date up to the pool's date, a quantity not `NULL` and not zero —
minus the excluded ids, whose quantity or amount reads `None`, or whose
`cost_basis_override` is stored (not `NULL` in SQL) but reads `None`. A `NULL` cost
basis is a row without one, such as a `BUY`, and is not counted. When there is any,
`_auto_cost()` raises `UnreadablePoolError(count)` before averaging. The error
carries the count only, never a transaction id: the pool can be another user's
broker, since the receiving side of a `TRANSFER` averages its partner's.

The guard is `_auto_cost()`'s, so it covers the costs written on rows — Auto rows,
and the giving leg's `_handover_cost()`; `POST /portfolio/wac` and the PAC planner
call `compute_wac_iterative()` directly, without it. Where it raises, nothing
averaged from that pool is written:

| Caller | On `UnreadablePoolError` |
|--------|--------------------------|
| `_compute_wac_for_auto_items(..., unreadable=None)` | With a list passed as `unreadable`, the item gets no cost and no `WACPreviewResultItem`, `(operation, index, count)` is appended to the list, and the other items go on. Without a list, the error raises |
| `delete_by_broker()` | The deletion of that broker fails whole (see [Broker Deletion](service.md#broker-deletion)) |
| `convert_lone_giving_legs()`, through `_handover_cost()` | That leg stays a `TRANSFER` without its partner, answered with the error's message as its reason; the other legs are converted (see [Lone giving legs](../../architecture/database/index.md#lone-transfer-legs)) |

`compute_wac_and_fx_issues()` passes no list yet — the batch's own refusal is wired
separately — so in a batch the error, like one from `_handover_cost()` on the giving
leg of a split `TRANSFER`, propagates out of `execute_batch()`.

### 🔗 Promote boundary {: #promote-boundary }

`TXPromoteBatchItem` has no `cost_basis_mode`, and `apply_promotes()` no longer
performs an automatic WAC calculation. A promote-specific resolved value arrives
as `resolved_fields.cost_basis_override` from the frontend merge flow (or another
API client). The promote stage applies it to the positive-quantity transfer leg
and clears it from the sender; without that key, the receiver keeps the cost basis
it already has. Either way the sender ends without one: before it applies
`resolved_fields`, `apply_promotes()` clears `cost_basis_override` and
`cost_basis_currency` on a side whose new type takes none (`cost_basis_allowed()`),
such as an `ADJUSTMENT` taking units out that a split left with a cost (decision
47).

Rows that are also present in `creates[]` or `updates[]` enter auto-WAC only
because that create/update item requested an auto mode, never because of the
promote item itself.

`validate_cost_basis()` checks the receiving side of a promoted pair like any
other row:

- a new row is checked as a create, unless it is in Auto: `costBasisRequired` on
  operation `create`, with its index;
- a saved row also present in `updates[]` is checked as that update, unless it is
  in Auto: the promote changes its type, so even an update of its notes alone is
  checked; and
- any other saved row without a cost basis gets `costBasisRequired` on operation
  `promote`, with the promote's index and `ref_id` set to that row
  (`_check_promoted_saved_cost_basis()`).

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

---

## 🔗 Related

- 🏗️ **[Transaction Service](service.md)** — Ordered batch stages and caller-owned transaction boundary
- ✂️ **[Split & Promote](split_promote.md)** — Promote's resolved cost-basis contract
- 📊 **[Lots Analysis Service](lots_analysis_service.md)** — WAC lines and their gaps
- 🛡️ **[Data Quality Banner](../../frontend/data-quality-banner.md)** — How missing pairs and missing cost bases reach the Dashboard
- 📖 **[Weighted Average Cost Theory](../../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md)** — Financial methodology
- 💱 **[Three-Pool Cash Model](../../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/index.md#6-three-pool-cash-model-per-broker-k_b-r_b-w)** — Capital and returns pools per broker, and how the engine books the exchange result on cash
- 🧠 **[FIFO Lot Engine](fifo_lot_engine.md)** — Per-lot alternative to a blended average
