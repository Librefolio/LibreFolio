# 📊 Lots Analysis Service

`backend/app/services/lots_analysis_service.py` is the orchestration layer behind `POST /portfolio/lots/analysis`.

It runs `FifoLotEngine` once, then converts engine output into `LotsAnalysisResponse`: FX-normalized values, qbq-aware valuations from the unified price resolver, lot/event histories, WAC series, income allocation, and valuation at cost on the days the asset has no price yet. Frontend consumer: `LotsAnalysisPanel.svelte`.

---

## 🗂️ Where the Code Lives {: #code-layout }

The service keeps the orchestration (`get_lots_analysis()`), the database loaders, the response builders — lot summaries (`_build_lot_summaries()`), Gantt segments (`_build_gantt_segments()`), event rows (`_build_lot_event_rows()`) — and the analysis' data-quality report (`_build_data_quality_report()`, `_report_gaps()`). The pure math it calls lives in the [financial math layer](../financial_math.md), as functions of `backend/app/services/financial_math/lots/` that take every input as an argument:

| Module | What it holds |
|--------|---------------|
| `prices.py` | What the lots read from the asset's `AssetPriceSeries`: `opening_reference_price()`, a lot's reference price at its opening (see [Reference Price](#reference-price)), and `last_day_without_observation()`, the last day valued at cost (see [Estimated-at-Cost Fallback](#estimated-at-cost-fallback)) |
| `conversions.py` | `FxRateResolver`; `convert_closure()` → `ConvertedClosure`, a closure's two legs each in its own currency at its own date, and `need_closure_rates()`, the two rates it reads (see [Closures: each leg at its own date](#closure-conversion)); the conversions each view needs: `collect_fx_needs()`, `collect_performance_fx_needs()`, `needs_market_series()`, `unconvertible_ids()` |
| `economic_events.py` | The engine's income and FEE/TAX inputs (`build_income_economic_events()`, `build_cost_economic_events()`, `build_engine_transactions()`), their outputs (`extract_income_outputs()`, `extract_cost_outputs()`), `WithheldEconomics` / `withheld_economics()` and `map_economic_groups()` |
| `histories.py` | The value, return, price and performance histories (`build_value_history()`, `build_return_history()`, `build_price_history()`, `build_performance_history()`) with their per-day snapshot helpers, `lot_history_end_date()`, `trim_dates()`, `known_realized_pnl()`, `known_cumulative_proceeds()` |
| `summary.py` | A lot's figures, read by the lot summary and the histories: `residual_cost()`, the original cost of the quantity still open (also the AI Export's `lot_residual_cost_basis()`); `lot_value()`, a lot's total value and P&L by direction; `lot_summary_figures()` → `LotSummaryFigures`, the lot summary's computed figures from its converted inputs — `_build_lot_summaries()` gathers those inputs and maps the result |
| `average_cost_lines.py` | `ALL_BROKERS`, and the broker and cumulative WAC history points (`build_broker_wac_history()`, `build_cumulative_wac_history()`, `average_cost_points()`) |

`FxRateResolver.load()` is the package's only async step and its only I/O: one `convert_bulk()` call for the rates registered since the previous load. The FIFO replay is in `financial_math/fifo/` ([FIFO Lot Engine](fifo_lot_engine.md)), the daily marks in `financial_math/price_marks.py` ([Price Resolver](price_resolver.md)). The functions of `lots/` and the service's sync builders are tested by `./dev.py test services lots-analysis-pure`.

---

## 🔌 API Contract

### 🛣️ Endpoint

```text
POST /portfolio/lots/analysis
```

Router entrypoint:

```python
@portfolio_router.post("/lots/analysis", response_model=LotsAnalysisResponse)
async def get_lots_analysis(body: LotsAnalysisQuery, ...):
    ...
    return await service.get_lots_analysis(
        user_id=current_user.id,
        asset_id=body.asset_id,
        broker_ids=body.broker_ids,
        date_from=date_from,
        date_to=date_to,
        target_currency=body.target_currency,
        selected_lot_ids=body.selected_lot_ids,
        requested_analyses=body.requested_analyses,
    )
```

If `date_range` contains min/max sentinels, router resolves them before calling service.

### 🧾 Request Body — `LotsAnalysisQuery`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `asset_id` | `int` | Yes | Asset to analyze |
| `broker_ids` | `list[int] \| None` | No | `None` = all accessible brokers |
| `date_range` | `OpenDateRangeModel \| None` | No | Limits emitted histories/visible intervals, not engine starting state |
| `target_currency` | `str \| None` | No | Defaults to global base currency |
| `selected_lot_ids` | `list[int] \| None` | No | Lot subset for lot-scoped analyses |
| `requested_analyses` | `list[LotAnalysisType]` | Yes | Non-empty, duplicates rejected |

### 🧩 `LotAnalysisType`

| Enum member | Response field | Meaning |
|-------------|----------------|---------|
| `LOT_SUMMARY` | `lots` | One row per lot with scalar metrics, states, custody, current valuation |
| `GANTT_TOPOLOGY` | `gantt_segments` | Custody fragments for Gantt lanes |
| `CUSTODY_HISTORY` | `custody_history` | Custody-only event subset |
| `EVENT_HISTORY` | `lot_events` | Full lot chronology: openings, splits, transfers, closures |
| `VALUE_HISTORY` | `value_history` | Per-lot `open_value`, `proceeds`, `total_value`, `pnl`, `income` |
| `RETURN_HISTORY` | `return_history` | Per-lot `total_return`, `relative_return`, `income` |
| `PRICE_HISTORY` | `price_history` | Per-lot market-price series |
| `BROKER_WAC_HISTORY` | `broker_wac_history` | Broker-scoped WAC time series |
| `CUMULATIVE_WAC_HISTORY` | `cumulative_wac_history` | Combined WAC time series |
| `PERFORMANCE_HISTORY` | `performance_history` | Asset-wide ROI/TWRR, ignores lot selection |
| `INCOME_EVENTS` | `income_events` | Dividend/interest markers allocated to open LONG lots |

### 📦 Response Shape — `LotsAnalysisResponse`

Top-level fields always present:

| Field | Meaning |
|-------|---------|
| `asset_id` | Requested asset |
| `target_currency` | Final response currency |
| `quote_base_quantity` | Asset qbq, needed by frontend price/WAC axis |
| `calculation_status` | `COMPLETE`, `DEGRADED`, or `FAILED` (public global status; an empty-but-valid analysis is `COMPLETE`). A `COMPLETE` engine run becomes `DEGRADED` when a conversion is missing — in a WAC line or in any other figure of the analysis — or a WAC line misses a cost basis (see [FX Conversion](#fx-conversion) and [WAC Lines](#wac-lines)). With `FAILED` the lot figures are withheld (see [A Failed Reconstruction](#failed-reconstruction)) |
| `calculation_metadata` | Broker scope, selection, requested/computed date bounds, generation date |
| `data_quality` | FIFO/data-quality issues mapped to UI-friendly DTOs |
| `economic_allocation_groups` | 3-level economic audit (income + FEE/TAX) mapped from the engine, `None` unless `LOT_SUMMARY` requested |
| `asset_orphan_income` / `asset_orphan_fees` / `asset_orphan_taxes` | Amounts that belonged to no eligible lot, kept at asset level (never dropped, never double-counted) |

All analysis payload sections are `None` unless explicitly requested — and, with `FAILED`, every section but the WAC lines (see [A Failed Reconstruction](#failed-reconstruction)).

---

## ⚙️ Processing Pipeline

Service entrypoint:

```python
async def get_lots_analysis(
    self,
    user_id: int,
    asset_id: int,
    broker_ids: list[int] | None,
    date_from: date_type | None,
    date_to: date_type | None,
    target_currency: str | None,
    selected_lot_ids: list[int] | None,
    requested_analyses: list[str | LotAnalysisType],
) -> LotsAnalysisResponse:
```

High-level flow:

1. Load accessible brokers, asset transactions, split ratios, broker shorting flags, `price_history`, asset income and FEE / TAX transactions. A split whose stored ratio fails `is_valid_split_ratio()` stays in the ratio map, so its row is still split-linked and the WAC lines still treat it as a split, but the FIFO engine skips it: no lot is rescaled, `lot_events` has no `SPLIT` row for it, and the analysis reports no issue (lot MF-D4).
2. Build one qbq-aware resolver series with `build_asset_price_series()`, from the `price_history` rows and the loaded transactions — before the engine, which reads it for reference prices (see [Unified Price Resolver](#unified-price-resolver)). Then read the transfer legs that cross the scope's edge with `read_transfers_at_scope_boundary()`: every later step reads the list it returns (see [Transfers Across the Scope's Edge](#scope-edge-transfers)).
3. When a requested analysis reads income, fees or taxes, build the engine's economic inputs first — income and FEE / TAX events and the BUY / SELL amounts that weight the FEE / TAX split, each converted at its own date (`build_income_economic_events()`, `build_cost_economic_events()`, `build_engine_transactions()`). Then build `reference_price_lookup()` over the series (see [Reference Price](#reference-price)) and run `run_fifo_lot_engine(...)`.
4. Resolve selected lots, and the days valued at cost: `at_cost_until = last_day_without_observation(price_series, history_dates)` (see [Estimated-at-Cost Fallback](#estimated-at-cost-fallback)).
5. Collect needed FX pairs with `collect_fx_needs()` / `collect_performance_fx_needs()`, then batch-load rates through `FxRateResolver`.
6. Extract the engine's **economic stage** outputs — income, FEE/TAX and net metrics — with `extract_income_outputs()` and `extract_cost_outputs()` (allocation itself happens inside the engine, not here).
7. Convert the marks of the days the requested analyses read into the two valuation maps, `market_prices` and `estimated_market_prices`, both from the same series.
8. When `BROKER_WAC_HISTORY` or `CUMULATIVE_WAC_HISTORY` is requested, compute the average-cost lines with one `compute_average_costs()` call (see [WAC Lines](#wac-lines)); their gaps — missing rates, unknown costs — are reported in step 10.
9. Emit only requested DTO sections.
10. Once every builder has run, report the gaps once, for the whole analysis: `_report_gaps()` adds to `data_quality` the WAC lines' gaps and every conversion `FxRateResolver` could not make (see [FX Conversion](#fx-conversion)).

Step 1's broker scope comes from `_get_scope_broker_ids()`: every broker the user can access, in any role, intersected with `broker_ids` when given. No owner share is applied anywhere in the analysis — quantities, values and P&L are each broker's full figures, unlike the portfolio summary, which scales an OWNER's brokers by their `share_percentage`. The lot modal says so next to its quantities (`brokers.lots.modal.absoluteQuantityTooltip`).

### ↔️ Transfers Across the Scope's Edge {: #scope-edge-transfers }

A scope can hold one leg of a transfer and not the other: `broker_ids` names the receiver alone, or a co-owner sees one
of the two brokers. The engine replays the scope's rows only, so on its own it could not pair that leg and would fail the
whole asset (`TRANSFER_PAIR_MISSING`). Instead, `read_transfers_at_scope_boundary()`
(`financial_math/lots/scope_boundary.py`, J-10, decision N76) reads the leg the way the scope sees it, as the
broker-scope Dashboard does:

| Leg | Read as | Effect |
|-----|---------|--------|
| In (quantity > 0) | An `ADJUSTMENT` in, at the leg's own `cost_basis_override` / `cost_basis_currency` (the Auto cost a receiving leg carries) | A new lot opens on the arrival day at that cost. Without a cost basis (old data) it is a costless adjustment: `MISSING_COST_BASIS`, `DEGRADED` |
| Out (quantity < 0) | An `ADJUSTMENT` out, at the market value of its own day: the resolver's mark brought to one unit (`compute_holding_value`), in the mark's currency | The lots close on the departure day; the scope realizes market − FIFO cost, the gain the units made while in it |
| Out, no observation on or before its day | An `ADJUSTMENT` out flagged `hands_over_at_own_cost` | Each fragment leaves at its own FIFO cost: realized 0. The day is one the analysis already values at cost (`CURRENT_PRICE_ASSUMED_AT_COST`) |

- **When.** Only when the partner (`related_transaction_id`) exists, sits at a broker outside the scope and pairs back:
  a `TRANSFER`, linked to the leg, of the same asset, of the opposite sign and the same absolute quantity — the checks of
  the engine's own pairing. A pair really missing or broken is left as it is, and the engine still fails it.
- **What is read of the partner.** Its pairing columns only (`_read_at_scope_boundary()` selects id, broker, asset,
  type, quantity and link): never an amount or a cost, so nothing of a broker outside the scope reaches the figures —
  for an owner filtering one broker as for a co-owner who sees only one.
- **Detached copies.** Each read leg is a `FifoInputTransaction` (type `ADJUSTMENT`, no link, amount 0) in the leg's
  place; the ORM rows are never changed. The split ratios and the price series come from the rows as loaded, before the
  reading: a `TRANSFER` or an `ADJUSTMENT` is never a split link nor an observation.
- **Every reader.** The engine, the histories, the conversions and the average-cost lines all read the returned list.
  `FifoInputTransaction.from_transaction()` hands a copy back as it is, so the flag survives
  `build_engine_transactions()`.
- **Performance.** `build_performance_history()` moves a read leg's market value of the day across the scope —
  money in for a leg that arrives, out for one that leaves — through `PerformanceSourceContext.boundary_legs`, exactly
  as it counts a transfer whose two legs the re-run over the accessible brokers holds. The two paths give the same
  series. The re-run reads the edge of the accessible brokers in turn, for a partner at a broker the user cannot see.
  On a day valued at cost a leg moves the cost of its units instead (see
  [Estimated-at-Cost Fallback](#estimated-at-cost-fallback)).
- **Yield on cost.** `financial_math/yield_on_cost.py` reads the arrivals alone, with `read_arrivals_at_scope_boundary()`
  (J-51): an arrival whose partner pairs back from a broker the user cannot see becomes an `ADJUSTMENT` in, and its
  partner leaves the replay, which would otherwise join a broker with no history and fail. A departure keeps its partner,
  because the yield on cost counts units in transit for the broker they left. It needs no price: the yield's cost is the
  Dashboard's average cost of the position, never the replay's.
- **The same rule as the Dashboard.** In a broker's own view the Dashboard counts an incoming leg's cost basis in the
  average cost and its market value as capital, and an outgoing leg's market value as the capital that left (lot 41,
  D2 and D5): lots and Dashboard agree broker by broker.

The timeline shows a read leg as an `ADJUSTMENT_IN` / `ADJUSTMENT_OUT` row.

### ⏳ Transfers In Transit at the End {: #in-transit-at-date-to }

The analysis reads the rows up to `date_to`, so a transfer still on its way that day (departure ≤ `date_to` < arrival,
in either order of the two legs' dates) would lose its arriving leg, and the engine would fail the asset
(`TRANSFER_PAIR_MISSING`) even over every broker (J-47). The Dashboard keeps such units in transit from the
departure to the arrival; the lots do the same:

- `_load_late_transfer_legs()` loads the partners, dated after `date_to`, of the scope's TRANSFER legs that sit in the
  scope (same asset, a `TRANSFER`), as detached `FifoInputTransaction` copies. They go to the engine only: no history,
  WAC line or rate reaches past `date_to`.
- The engine replays up to `date_to` (`replay_until`): the arrival is not applied, so the fragment stays `IN_TRANSIT`,
  valued at market like any open fragment. The lot carries the `IN_TRANSIT` state, the Gantt draws the transit to the
  end, and the timeline has the `TRANSFER_DEPART` row and no `TRANSFER_ARRIVE` (`_build_transfer_rows()` writes no
  arrival for a fragment still in transit).
- The re-run over the accessible brokers of `PERFORMANCE_HISTORY` does the same. Its performance counts the transit
  value only when both brokers are in the requested scope (`_fragment_in_scope`), as the Dashboard's combined view.
- A partner outside the scope is read at the scope's edge instead (see
  [Transfers Across the Scope's Edge](#scope-edge-transfers)), whatever its date.

### 🛑 A Failed Reconstruction {: #failed-reconstruction }

A replay that hits a quantitative failure is `FAILED`: a code of `_QUANTITATIVE_FAILURE_CODES` — a sale or a transfer
beyond the quantity held (`FIFO_SOURCE_QUANTITY_MISSING`), a transfer or an adjustment out of SHORT inventory
(`SHORT_TRANSFER_NOT_SUPPORTED`, `SHORT_ADJUSTMENT_NOT_SUPPORTED`), a transfer leg without its partner
(`TRANSFER_PAIR_MISSING`). The lots it leaves do not match what the account holds, and every later event consumes the
wrong ones, so every lot figure would be wrong. Missing data is declared, never shown wrong (J-12, decision N81): right
after the engine, the service keeps only the analyses that do not read the lots.

- **Withheld.** Every section that reads the lots is `None`, requested or not: `lots`, `gantt_segments`,
  `custody_history`, `lot_events`, `value_history`, `return_history`, `price_history` (one series per lot),
  `performance_history`, `income_events` and `economic_allocation_groups`, and the three orphan totals. No rate is
  registered and no market value is computed for them.
- **Kept.** The WAC lines (`broker_wac_history`, `cumulative_wac_history`) come from the transactions, not from the
  replay: they are built as usual, with their gaps. So are `quote_base_quantity`, `calculation_metadata` — whose
  `requested_analyses` are still those asked for — and `data_quality`.
- **The issues.** `data_quality` holds the issues that fail the replay and the gaps of the WAC lines (`_report_gaps()`:
  their missing rates, `MISSING_COST_BASIS`). The issues about what is withheld are left out: `REFERENCE_PRICE_FALLBACK`
  / `REFERENCE_PRICE_UNAVAILABLE`, `ASSET_INCOME_NO_ELIGIBLE_LOTS` / `ASSET_COST_NO_ELIGIBLE_LOTS`,
  `CURRENT_PRICE_ASSUMED_AT_COST` and the rates of the lot figures.
- **The row to fix.** `_build_data_quality_report()` gives each issue that fails the replay
  (`fails_the_replay()`, `financial_math/fifo/models.py`) two more `message_params`: `transaction_date`, the ISO date of
  its `transaction_id`, and `fails_analysis: true`, so a reader needs no list of codes. `transaction_id` is always a
  row of the scope — for a transfer, the giving leg (see [Depart](fifo_lot_engine.md#depart)); a copy read at the
  scope's edge or still in transit keeps the id of its row. `related_transaction_id` is the partner, never the row to
  fix.

`analysis_failure_codes(response)` reads them back: the sorted unique codes of the issues that carry `fails_analysis`.
The AI Export declares a `FAILED` asset with them instead of exporting its lots (see
[Snapshot Data Tables](../../architecture/patterns/ai_export_composition.md#snapshot-data-tables)). A `DEGRADED`
analysis is not concerned: its gaps are isolable, and its figures stay.

### 💱 FX Conversion {: #fx-conversion }

`FxRateResolver` (`financial_math/lots/conversions.py`) is a thin prefetch + conversion helper:

- `need(currency, as_of_date)` registers required pairs
- `load(session)` calls `convert_bulk(...)` once, for the pairs registered since the previous load
- `convert(amount, currency, as_of_date)` applies date-specific conversion into `target_currency` — an amount without a currency is taken as already in it; a conversion it cannot make — a non-`None` amount in a currency other than the target, with no loaded rate for that `(currency, date)` — returns `None` and is recorded
- `missing_pairs()` returns the recorded misses as `WACMissingPairInfo(pair, dates)`, one entry per `FROM/TO` pair with its dates sorted

Service converts:

- lot opening cost and opening unit price
- each selected lot's reference price, from its currency at the lot's opening date (see [Reference Price](#reference-price))
- event-history opening rows (`BUY` / `ADJUSTMENT_IN`, `_build_opening_and_split_rows()`): the opening unit price, from the **lot's** currency at the opening date — a `BUY`'s own currency, the cost basis's for an `ADJUSTMENT_IN` priced by its `cost_basis_override` (see `FifoLot.currency` in [FIFO Lot Engine](fifo_lot_engine.md)); and `opening_value`, the lot's original cost at the opening date — the summary's `original_cost`, in the currency of `unit_price`; for these rows `collect_fx_needs()` registers the lot's currency on every opening event
- closures, through `convert_closure()` alone: each leg in its own currency at its own date — the lot's side at the lot's opening date, the closing side at the closure date — an `ADJUSTMENT_OUT`'s value handed over at cost included (see [Closures: each leg at its own date](#closure-conversion))
- Gantt fragment unit prices
- native resolver marks from `build_asset_price_series()`
- dividend / interest and FEE / TAX amounts, and the BUY / SELL amounts that weight the FEE / TAX split (economic-stage inputs)
- performance-history external flows

**No native fallback.** A figure that needs a missing rate is never computed from the unconverted amount — it is `None`, or it has no point:

- **Daily valuation**: a mark whose rate is missing leaves that day unvalued — `market_prices[date]` is `None`, the day has no price-history point, and a still-open lot has no value or return point that day. Never at cost: only a `MISSING` day, with no observation on or before it (up to `at_cost_until`), values a lot at cost; see [Estimated-at-Cost Fallback](#estimated-at-cost-fallback).
- **Value and return histories** (`_lot_value_basis()` and `_lot_snapshot_on_date()`, shared by both builders): a lot whose original cost — or, for a SHORT, its proceeds — has no rate gets no point; a lot's series stops the day before the first closure whose proceeds — for a SHORT, its buy-back cost — have no rate (`_closure_prefix(lot, closures, fx_resolver, leg)`, in `financial_math/lots/histories.py`, returns the running sum of that converted leg by close date and that date). Same rule as the [WAC Lines](#wac-lines): a point that cannot be computed is omitted. Within an emitted point, the income, fee and tax fields that a degraded economic pool withholds — and the figures read from them — are `None` instead (see [Economic events and degraded pools](#degraded-economic-pools)).
- **Performance history**: a BUY amount, an ADJUSTMENT's money — an ADJUSTMENT-in's, or the cost an ADJUSTMENT-out with a cost basis hands over (`_adjustment_native_cost()` / `adjustment_cash_flow_cost()`) — or a SELL closure's proceeds without a rate — the sale's currency at its date — set `invalid_external_flow_from`: ROI and TWRR are `None` from that date. `collect_performance_fx_needs()` registers each of those rates; for an ADJUSTMENT-out with a non-zero cost basis, `cost_basis_currency` (the asset's currency when empty) at the row's date.
- **Lot summary**: `original_cost` and `opening_unit_price` are `None` when the rate at the opening date is missing; `cumulative_proceeds` (`known_cumulative_proceeds()`) when one closure's closing rate is missing — for a SHORT lot's proceeds, the opening-date rate — and `realized_pnl` (`known_realized_pnl()`) when one closure misses either of the two rates it reads (see [Closures: each leg at its own date](#closure-conversion)); `reference_unit_price` when the rate of its currency at the opening date is missing, and `reference_price_source` whenever `reference_unit_price` is `None` — a reference that could not be converted has no source, as in the return history. `total_value` (when the proceeds have no rate), `pnl`, `market_pnl`, `total_pnl`, `cash_yield`, `total_return`, `net_total_pnl`, `net_total_return` and `annualized_return` are `None` when one of their inputs is unknown — an amount above, or the income, fees or taxes a degraded economic pool withholds — and the estimated-at-cost branch values no lot without a converted cost.
- **Gantt topology**: `GanttSegmentSchema.unit_price` is `None` when the rate at the fragment's `start_date` is missing.
- **Economic events** (income, FEE, TAX): a missing rate on an event degrades its pool, and one on a trade can degrade a FEE / TAX pool that the trade weights; the figures a degraded pool feeds are withheld — see [Economic events and degraded pools](#degraded-economic-pools).

The misses are reported once, after every builder: `_report_gaps()` merges `missing_pairs()` with the WAC lines' gaps into `data_quality` (see [WAC Lines](#wac-lines)), and any of them turns a `COMPLETE` run `DEGRADED`. Only what is returned is converted, so the report holds no gap of a figure nobody reads: event rows (`_build_lot_event_rows()`) are built only when `CUSTODY_HISTORY` or `EVENT_HISTORY` is requested, and the daily valuation covers every history day only for the value, return, price and performance histories — a `LOT_SUMMARY` alone values just the last day, the only one it reads.

The WAC lines do not go through `FxRateResolver`: `compute_average_costs()` converts each acquisition itself, at its own date.

#### 💱 Closures: each leg at its own date {: #closure-conversion }

A closure has two legs, and each converts in its own currency at its own date (developer decision 26): the lot's side from the lot's currency at the lot's `opening_date` — the opening rate, a LONG lot's purchase rate — and the closing side from the closure's `close_currency` at its `close_date` — the closing rate, a LONG lot's sale rate. `close_currency` is the currency of the closing price, which need not be the lot's: a lot moved to a broker of another currency is sold in that currency, an `ADJUSTMENT_OUT` hands its units over in its cost basis's currency (see [Closure currency](fifo_lot_engine.md#closure-currency)).

The rule has one home, `convert_closure(closure, lot, fx_resolver)` (`financial_math/lots/conversions.py`), which returns a `ConvertedClosure` in the target currency:

| Field | Converted from |
|-------|----------------|
| `open_unit_price` | `closure.open_unit_price`, at the opening rate |
| `close_unit_price` | `closure.close_unit_price`, at the closing rate |
| `proceeds` | `closure.proceeds`, at the closing rate: a sale's cash, or the value an `ADJUSTMENT_OUT` hands over at cost; 0 on a SHORT closure |
| `cost` | The leg the closure gives up: for a LONG lot, the purchase cost of the units, `quantity × open_unit_price` at the opening rate; for a SHORT lot, the purchase that closes it, `quantity × close_unit_price` at the closing rate |
| `realized_pnl` | `realized_gain(proceeds, cost)` (`financial_math/returns.py`), the proceeds minus `cost`: for a LONG lot its closing leg, the `proceeds` above; for a SHORT lot its opening leg, the proceeds of its opening sale, `quantity × open_unit_price` at the opening rate |

`realized_gain()` is the function the Dashboard applies to its realized sales too (`portfolio_service.py`: proceeds at the sale date, cost at the purchase dates), and each caller keeps its own rule for summing: the Dashboard sums the sales it can value and reports the others in the data quality, while a lot with one unknown closure has an unknown realized P&L.

The engine's native `LotClosure.realized_pnl` is never read: it is `None` whenever `close_currency` is not the lot's. A missing rate leaves `None` the figures that need it, never one computed from native amounts — `close_unit_price` and `proceeds` need the closing rate, `open_unit_price` the opening rate, `cost` the rate of its leg, `realized_pnl` both. `need_closure_rates()` registers the two, `(close_currency, close_date)` and `(lot.currency, opening_date)`: `collect_fx_needs()` calls it for the closures of the lot summary, the return history and the event rows, `collect_performance_fx_needs()` for a LONG lot's SELL closures.

Every reader converts closures through `convert_closure()`:

- **Lot summary**: `realized_pnl` (`known_realized_pnl()`) sums the closures' and is `None` as soon as one of them is; `cumulative_proceeds` (`known_cumulative_proceeds()`) sums a LONG lot's closure proceeds — a SHORT lot's are those of its opening sale, converted at the opening date;
- **Value and return histories**: the running sums of `_closure_prefix(lot, closures, fx_resolver, leg)` (`financial_math/lots/histories.py`) — a LONG lot's closure `proceeds`, a SHORT lot's `cost`;
- **Performance history**: the SELL closures' proceeds, its inflows;
- **Event history**: the closure rows (`_build_closure_rows()`) — `unit_price` and `close_unit_price` at the closing rate, `open_unit_price` at the opening rate, `proceeds` and `realized_pnl` as above.

The lot summary keeps `market_pnl = pnl − realized_pnl`. Every closure's cost converts at the opening date, like `original_cost`, so a LONG lot's `market_pnl` is its open value minus the cost of its open units at the purchase rate: a fully closed LONG lot has a `market_pnl` of 0 and a `realized_pnl` equal to its `pnl`, and the exchange-rate move between purchase and sale is realized with the units, as on the Dashboard. The theory page [FIFO Lot Analysis](../../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md) works an example through.

An `ADJUSTMENT_OUT` with a cost basis hands every fragment over at the row's per-unit cost, in that cost's currency — `cost_basis_currency`, the lot's when empty (see [Hand-over at cost](fifo_lot_engine.md#handover-at-cost)): its proceeds convert from that currency at the row's date and realize against the lot's cost at the opening date, whatever the lot's currency. The performance history reads the row instead, so its outflow is always the whole `|quantity| × cost_basis_override`, converted from `cost_basis_currency` (the asset's currency when empty) at the row's date.

#### 🧾 Economic events and degraded pools {: #degraded-economic-pools }

An income / FEE / TAX event without a rate still enters the engine with its native amount, only as a placeholder: the engine then places it — pools it, matches it, lets a TAX follow the income it taxes — exactly as it would place a converted one. `_engine_target_amount()` hands that amount over, for the events and for the BUY / SELL amounts that weight the FEE / TAX split, and the resolver records the miss. `unconvertible_ids()` collects the events (`unconvertible_event_ids`) and the trades (`unconvertible_trade_ids`) without a rate on their date, and `withheld_economics()` finds the engine pools (`EconomicAllocationGroup`) they degrade:

| Pool | Degraded when | Unknown |
|------|---------------|---------|
| **Amount-degraded** | One of its source events is in `unconvertible_event_ids` | Its target-currency amount, hence every target share of it |
| **Split-degraded** | A trade-weighted FEE / TAX rule (`SAME_DAY_TRADES`, `SAME_DAY_MIXED_TRADES`, `PREVIOUS_DAY_TRADES`), with a weighting trade in `unconvertible_trade_ids` and weighting trades in more than one currency | Its split: every operation weight and every per-lot share |

When every weighting trade is in one currency, the pool is not split-degraded: the trades share one date, hence one rate, and their native placeholders keep the exact ratios.

`WithheldEconomics` records, per lot, the date from which its income (`income_from`), fees (`fees_from`) and taxes (`taxes_from`) are unknown — the date of the earliest degraded pool of that kind that allocates to the lot — with the degraded pool indexes (`amount_degraded`, `split_degraded`), `unconvertible_event_ids` and the kinds whose orphan pool is degraded (`orphan_unknown`). The response withholds:

- **Lot summary** (`_build_lot_summaries()`): on a lot a degraded pool reaches, that kind's `asset_income`, `allocated_fees` or `allocated_taxes` is `None`, and so is every figure that reads it — `total_pnl`, `cash_yield` and `total_return` read the income; `net_total_pnl`, `net_total_return` and `annualized_return` read all three. The lot's `net_metrics_status` is `"UNAVAILABLE"` (`withheld.reaches(lot_id)`).
- **Value and return histories** (`_economics_on_date()`, `_known_prefix_on_date()`, `_lot_returns()`): each kind is `None` from its date on — the value history's `income`, `allocated_fees` and `allocated_taxes`, and its `net_pnl` with the fees or the taxes; the return history's `income`, its `total_return` with the income, and its `net_total_return` with any of the three. An earlier date sums only earlier pools, all of them known.
- **Income events**: `LotIncomeEventSchema.amount` is `None` for an event in `unconvertible_event_ids`.
- **Orphans**: `asset_orphan_income`, `asset_orphan_fees` or `asset_orphan_taxes` is `None` when an orphan pool of that kind is degraded.
- **Audit** (`map_economic_groups()`): an amount-degraded pool has `target_pool_total`, `target_orphan` and each lot allocation's `target_amount` set to `None`; a split-degraded pool has each operation `weight` and each lot allocation's `native_amount` and `target_amount` set to `None`. The native pool total, the native orphan and each lot's `weight` inside an operation — a quantity ratio — stay.

**Orphan issues.** The engine builds an orphan pool's `ASSET_INCOME_NO_ELIGIBLE_LOTS` / `ASSET_COST_NO_ELIGIBLE_LOTS` issue with the pool's `target_amount` and `target_currency` in its params. `_build_data_quality_report()` passes them through `_orphan_issue_params()`: for an amount-degraded orphan pool — matched by the issue's `transaction_id`, the pool's first source — the issue states the pool in its own currency, `target_amount` = `native_pool_total` and `target_currency` = `native_currency`, so the banner shows an orphan 70 VND dividend without a rate as "70 VND", never "70 EUR". The message keys keep their `target_` names: such an issue holds a native amount and currency under them, and summing `message_params.target_amount` across issues would mix currencies. A convertible orphan pool keeps its converted amount in the target currency.

The native placeholder therefore never reaches the response.

### ⚠️ qbq Scaling Gotcha {: #qbq-scaling-gotcha }

!!! warning "Two price scales coexist"

    `price_history.close` is quoted **per `quote_base_quantity`**.

    `opening_unit_price`, closure unit prices, and WAC values are **per single unit**.

    For bonds this mismatch is dangerous: comparing raw `opening_unit_price` with raw market price mixes
    two scales and historically caused huge fake returns/P&L. Example: a bond can trade near `100`, while
    `opening_unit_price` is near `1` because cost was divided by nominal quantity.

    The analysis fixes this in two places:

    - **Valuation path**: `lot_summary_figures()` (`financial_math/lots/summary.py`, the lot summary) and the
      `financial_math/lots/histories.py` functions `build_value_history()`, `build_return_history()` and
      `build_performance_history()` call
      `compute_holding_value(..., quote_base_quantity)` so `open_value = (qty / qbq) * price`.
    - **Reference-price fallback path**: `opening_reference_price()` (`financial_math/lots/prices.py`)
      multiplies `lot.opening_unit_price * quote_base_quantity` when the lot has no market reference:
      opened by a `BUY` or a short-opening `SELL`, or by an `ADJUSTMENT_IN` with no observation on or
      before its opening date (see [Reference Price](#reference-price)).

Exact fallback scaling code:

```python
scale = quote_base_quantity if quote_base_quantity > 0 else 1
return lot.opening_unit_price * scale, lot.currency, lot.opening_date, "exact"
```

That multiplication is **only** for the lot's own price. Resolver marks — market quotes, and trade prices already lifted by `build_asset_price_series()` — arrive in per-qbq scale and must **not** be multiplied again.

---

## 🧭 Unified Price Resolver {: #unified-price-resolver }

`LotsAnalysisService` uses `backend/app/services/financial_math/price_marks.py` as the single daily mark path —
the resolver's full contract (tiers, staleness semantics, qbq scale, the "only valuation path"
invariant) lives in its own page: [Price Resolver](price_resolver.md).

```python
price_series = build_asset_price_series(
    price_rows=[(row.date, row.close, row.currency) for row in prices],
    transactions=transactions,
    split_linked_tx_ids=set(split_ratios_by_tx_id),
    asset_currency=asset.currency,
    quote_base_quantity=quote_base_quantity,
)
mark = price_series.resolve(current_date)
```

The series is built once, before the FIFO engine runs, from the `price_history` rows `_load_prices()` reads — the window and the last quote before it — and from the loaded transactions, those of the brokers in scope: each of their `BUY` and `SELL` rows with an amount is a trade observation. It decides three things:

1. **The reference price** of a lot opened by an `ADJUSTMENT_IN`, which the engine reads while it replays (see [Reference Price](#reference-price)).
2. **The days valued at cost**: those with no observation on or before them, up to `at_cost_until` (see [Estimated-at-Cost Fallback](#estimated-at-cost-fallback)).
3. **The daily valuation**: the two maps below.

Resolution tiers are owned by `AssetPriceSeries.resolve()`:

| Tier | `MarkSource` | Meaning |
|------|--------------|---------|
| 1 | `MARKET` | Same-day asset-system `price_history.close`. |
| 2 | `TRADE_AVG` | Same-day `BUY`/`SELL` average. An `ADJUSTMENT` is never an observation, with or without a cost basis. |
| 3 | `CARRIED` | Last observation carried forward (LOCF), market- or trade-origin. |
| 4 | `MISSING` | No observation on/before the day. |

Marks stay in **native currency** and on the market × `quote_base_quantity` axis. The service converts `mark.unit_price` with `FxRateResolver.convert(..., current_date)`, so carried foreign marks use FX for the **valuation date**, not the original observation date.

Both internal maps are built from this same resolver:

- `market_prices[date] = target-currency mark or None` feeds lot summaries, value/return history, performance NAV, and transfer valuation.
- `estimated_market_prices[date] = (target-currency mark, mark.estimated)` feeds `PRICE_HISTORY`.

The old duplicate map pattern (`_build_market_price_map` plus `_build_estimated_market_price_map`) is gone in shipped code. There is no separate market-only valuation path to document.

`ResolvedMark.estimated` means **TRADE-origin**, including a trade mark carried forward. A real market quote carried forward is stale (`price_backward_fill`) but not estimated.

### 🎯 Reference Price {: #reference-price }

A lot's reference price is the denominator of its Open Return, `relative_return = market price / reference − 1`. The engine resolves one only when an `ADJUSTMENT_IN` opens a LONG lot (`_apply_adjustment_in()`): a lot opened by a `BUY` or a short-opening `SELL` has none and is compared with its own price — a trade is a price. The service hands the engine `reference_price_lookup(asset_id, opened_at)`, which reads `price_series.resolve(opened_at)`:

| Mark on the opening day | What the engine stores | Engine issue |
|-------------------------|------------------------|--------------|
| `MARKET`: a quote of that day | `mark.unit_price`, `reference_price_source="exact"` | — |
| `TRADE_AVG`: no quote, that day's `BUY` / `SELL` average | `mark.unit_price`, `"fallback"` | `REFERENCE_PRICE_FALLBACK` |
| `CARRIED`: a quote or a trade mark of an earlier day | `mark.unit_price`, `"fallback"` | `REFERENCE_PRICE_FALLBACK` |
| `MISSING`: no observation on or before that day | `reference_unit_price=None`, `"unavailable"` (the lookup returns `None`) | `REFERENCE_PRICE_UNAVAILABLE` |

An `ADJUSTMENT` is never an observation (developer decision P2): a lot opened by an opening position, a succession or a transfer from an untracked broker is compared with the market — the last quote, or a `BUY` / `SELL` more recent than it — and with its own cost basis only when the asset has no observation on or before its opening day.

`opening_reference_price(lot, price_series, quote_base_quantity)` (`financial_math/lots/prices.py`) gives the lot summary, the return history and `collect_fx_needs()` the reference as `(price, currency, date, source)`:

- a lot with a `reference_unit_price` keeps it, in the currency of the mark it came from (`price_series.resolve(lot.opening_date).currency`), dated `lot.opening_date`: the reference converts at the rate of the day it stands for, never at the date of an older observation it was carried from (developer decision P21: every amount at the rate of its day);
- any other lot falls back to its own price, `lot.opening_unit_price × quote_base_quantity`, in the lot's currency at the opening date, with source `"exact"` (see [qbq Scaling Gotcha](#qbq-scaling-gotcha)). An `ADJUSTMENT_IN` without a cost basis opens its lot at a unit price of 0, so that lot has no `relative_return`.

`collect_fx_needs()` registers that `(currency, opening date)` for each selected lot when `LOT_SUMMARY` or `RETURN_HISTORY` is requested. A reference whose rate is missing is `None`, and so is its `reference_price_source`, in the summary and in the return history, whose point then has no `relative_return`.

---

## 💸 Economic Stage — Income, FEE/TAX & Net Metrics

Since FIFO v5 the **allocation** of asset-linked income (`DIVIDEND` / `INTEREST`) and asset-linked cost
(`FEE` / `TAX`) happens **inside the engine's economic stage** (see
[FIFO Lot Engine](fifo_lot_engine.md)), not in the service. The service only **extracts** the already-computed
per-lot accumulators and audit groups, withholding what a missing rate leaves unknown, through the
functions of `financial_math/lots/economic_events.py`:

- `extract_income_outputs(engine_result, ...)` reads `engine_result.economic_accumulators_by_lot[*].gross_income`
- `extract_cost_outputs(engine_result, ...)` reads `.allocated_fees` / `.allocated_taxes`
- `map_economic_groups(...)` maps the 3-level audit into `economic_allocation_groups`
- `withheld_economics(...)` finds the pools a missing rate degrades, whose figures the response withholds (see [Economic events and degraded pools](#degraded-economic-pools))

!!! warning "Allocation rule moved and changed"

    The pre-v5 same-day rule `w_i(t) = OpenQty_i(t) / Σ OpenQty_j(t)` no longer applies. Income eligibility
    is now **D-1** (`OpenQty_i(D-1)`) and **broker-scoped** to the paying broker, and FEE/TAX use a
    deterministic operation-matching ladder. The math lives in the engine; see the theory page
    [FIFO Lot Analysis](../../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md).

### 📤 Extracted outputs

- `income_by_lot` → scalar cumulative income for `LotSummarySchema.asset_income`
- `income_prefix_by_lot` → per-date cumulative prefixes for value/return histories
- `income_events` → chart markers with source tx and affected lot ids
- `fees_by_lot` / `taxes_by_lot` → scalar `allocated_fees` / `allocated_taxes`, plus per-date prefixes for history

### 🧮 Net metrics (`LotSummarySchema`)

FEE/TAX are stored as **positive magnitudes** already converted to `target_currency`, and net metrics are
derived only when they can be meaningful:

```text
net_total_pnl    = total_pnl - allocated_fees - allocated_taxes          # total_pnl INCLUDES income
net_total_return = net_total_pnl / original_cost       (original_cost > 0)
```

History builders expose their own net lines: `build_value_history()` emits
`net_pnl = pnl - allocated_fees - allocated_taxes` (**pnl excludes income**), while `build_return_history()`
emits an income-inclusive `net_total_return`. The asymmetry is intentional — each net line mirrors its gross
counterpart minus costs.

!!! note "`net_metrics_status`"

    A lot that a degraded economic pool reaches is emitted with `net_metrics_status = "UNAVAILABLE"`
    (`withheld.reaches(lot_id)`): its income, fees or taxes are unknown, and so are its net figures (see
    [Economic events and degraded pools](#degraded-economic-pools)). Every other lot is `"AVAILABLE"`. The status
    speaks only for the economic pools: a net figure can also be `None` because its total P&L or its opening value
    needs a missing rate, with the status still `"AVAILABLE"`; every missing pair goes to `data_quality` (see
    [FX Conversion](#fx-conversion)).

### 🧺 Orphans & conservation

When income or FEE/TAX has no eligible lot (e.g. a cost after the position is fully closed), the amount is
**not dropped**: it is returned at asset level as `asset_orphan_income` / `asset_orphan_fees` /
`asset_orphan_taxes` and surfaced as a `ASSET_INCOME_NO_ELIGIBLE_LOTS` / `ASSET_COST_NO_ELIGIBLE_LOTS`
data-quality issue. The engine guarantees, per pool, `Σ allocated + orphan == converted pool total`. For a pool
whose amount has no rate, it conserves the native placeholder instead: the response withholds that pool's target
figures and, for an orphan pool, the asset-level orphan total of its kind, and the orphan issue states the pool in
its own currency (see [Economic events and degraded pools](#degraded-economic-pools)).

!!! info "Costs without an asset"

    `FEE` / `TAX` with `asset_id = null` never enter the FIFO/lots analysis at all — they are handled by the
    Portfolio Engine. Only asset-linked costs can produce allocated net figures here.

---

## 🧮 Estimated-at-Cost Fallback {: #estimated-at-cost-fallback }

A day with no observation on or before it — no `price_history` close (`_load_prices()` reads the window and the last quote before it) and no `BUY` or `SELL` with an amount among the loaded transactions — values an open LONG lot at its cost: the per-day rule of the Dashboard's `DailyStateBuilder._value_held_position()` (see [Price Resolver — No observation: valued at cost](price_resolver.md#valued-at-cost)). The resolver carries every observation forward, so such days only come before the asset's first one. The service finds them once, after the engine run:

```python
history_dates = list(_date_range(computed_from, actual_to))
at_cost_until = last_day_without_observation(price_series, history_dates)
```

`actual_to` is the requested `date_to` (today when it is not given), never later than `latest_range_end()` (tomorrow,
`utils/datetime_utils.py`): the histories walk every day of that range, and an end far in the future held the instance
(R13-SEC7-1). The response's `requested_date_to` and `computed_date_to` carry that bounded end.

`computed_from` is the first transaction's date, and `EARLIEST_RANGE_START` (1 January 1900, same module) at the
earliest (R13-SEC8): a transaction stored centuries back made every history walk every day since. The response's
`computed_date_from` carries it. From it start `history_dates`, the window `_load_prices()` reads and the per-day rates
of the market series (`collect_fx_needs()`). `display_from`, the start `trim_dates()` cuts the histories to, is the
requested `date_from` (or `computed_from`), clamped to the same floor; `requested_date_from` stays as requested. A
transaction dated before the floor still enters the FIFO engine on its own date, so the lot it opens or closes counts,
its history points from the floor on; `build_performance_history()` carries the flows dated before the first NAV day
into that day, like any flow before the first mark. A transfer leg needs the value of its own day: dated before the
floor, that day has no observation on or before it, so the leg moves the cost of its units, as on any day valued at
cost (J-33); only when the first history day already has an observation, a quote stored before the floor, has the leg
neither a price nor a cost, and the ROI/TWRR series stops from its date on — here, the whole series.

`last_day_without_observation()` (`financial_math/lots/prices.py`) returns the last of the ascending days whose `price_series.resolve()` is `MISSING`: the day before the first observation, `actual_to` when the asset has none, `None` when the first transaction's day already has one — a quote before it included. The days valued at cost are `[computed_from, at_cost_until]`, whether or not the asset is priced later:

| Reader | What it does with `at_cost_until` |
|--------|-----------------------------------|
| `build_value_history()`, `build_return_history()` | Pass `at_cost = current_date <= at_cost_until` to `_lot_snapshot_on_date()` (see below) |
| `build_performance_history()` | On such a day without a mark, the NAV of the open fragments in the scope at cost, and a transfer that day moves the cost of its units (see below, J-33) |
| `_build_lot_summaries()` | `estimated_mode = at_cost_until == actual_to`: the summary reads the end date only, so it is at cost only when that day has no observation — when the asset has none at all |
| Data quality | For an analysis that reads prices (`needs_market_series()`), one `CURRENT_PRICE_ASSUMED_AT_COST` warning (`dataQuality.currentPriceAssumedAtCostRange`) with `date_from = computed_from` and `date_to = at_cost_until`: exactly the days valued at cost. No warning when `at_cost_until` is `None` |
| FX needs | When an analysis reads income (`needs_income_alloc`), every lot's currency at its opening date, the rate of the cost those days read; for `PERFORMANCE_HISTORY`, `collect_performance_fx_needs(at_cost_until=…)` registers the same for every LONG lot of the replay it reads |

In the value and return histories, `_lot_snapshot_on_date()` (`financial_math/lots/histories.py`) values a day without a `market_price` this way:

- a lot with no open quantity left is valued from its closures alone, on any day;
- on an `at_cost` day, a still-open LONG lot is worth `open_quantity × original_cost / original_quantity`, its cost converted at the opening date — a lot whose cost has no rate has no point at all (see [FX Conversion](#fx-conversion));
- after `at_cost_until`, a `market_price` of `None` can only be a mark whose rate is missing: a still-open lot has no point that day, never one at cost.

The return history has no `relative_return` on an `at_cost` day. An asset first priced after a lot opened by an adjustment therefore shows that lot at cost — a flat value line, no market P&L — from its opening to the day before the first quote, `BUY` or `SELL`, then at the mark.

In the summary (`lot_summary_figures()`), `estimated_mode` values the remaining quantity of a LONG lot at residual cost, provided the cost itself converts (`original_cost`, converted at the opening date, is not `None`; otherwise the lot is not valued):

```python
open_value = residual_cost(original_cost, lot.open_quantity, lot.original_quantity)
value_source = "ESTIMATED_AT_COST"
market_pnl = Decimal("0")
```

Outside `estimated_mode` the end date always has a mark — every observation is on or before it — so a lot's latest mark is `None` only when its rate is missing: the lot then has no value and no `value_source`, as the `LotSummarySchema.value_source` description says.

Implications:

- `LotSummarySchema.value_source = "ESTIMATED_AT_COST"` only for an asset with no observation up to the end date — one held only through adjustments or transfers, with no quote
- `total_value`, `total_pnl`, `cash_yield`, `total_return` remain usable, as long as the proceeds and realized P&L they read convert (see [FX Conversion](#fx-conversion))
- `relative_return` stays `None`: there is no market price to compare with the reference
- data quality report adds `CURRENT_PRICE_ASSUMED_AT_COST`, from the first transaction to the end date

A TRADE-origin mark is a price: valuation uses it, the lot summary's `value_source` is then `MARKET_PRICE` — the label of any mark — and the price-history point carries `estimated=True`. Only a `BUY` or a `SELL` gives one: an `ADJUSTMENT` never does, with or without a cost basis (see [Price Resolver](price_resolver.md#the-daily-model)).

`build_performance_history()` reads the same days at cost (J-33). On a day `<= at_cost_until` without a mark, `_nav_at_cost()` values the open fragments in the scope at their lot's cost converted at the opening date (`_cost_at_opening()`, the value history's own rule); a day where one of them belongs to a SHORT lot, or its cost has no rate, has no NAV point. A transfer that day moves the cost of its units, never an unknown market value: a leg read at the scope's edge brings its own cost basis when it arrives and, when it leaves — handed over at its own cost — the cost of the pieces it closes (`_boundary_leg_cost()`); a transfer the re-run holds moves the cost of the pieces of its pair (`_moved_cost()`, from the pair's fragments). So the series starts on the first day held, ROI and TWRR are 0 while the position sits at cost, and the TWRR chain holds the move from cost to the first price, as the ROI does: before, the first NAV was the first mark, the base of the TWRR, and that move fell outside its chain. An asset with no observation has ROI and TWRR 0 every day. The price history has no point on the days at cost.

---

## 🎯 Selection Model

Backend method:

```python
def _resolve_selected_lot_ids(self, selected_lot_ids: list[int] | None, lots_by_id: dict[int, FifoLot]) -> list[int]:
    if selected_lot_ids is None:
        return list(lots_by_id)
    ...
    return list(dict.fromkeys(selected_lot_ids))
```

Meaning at raw API level:

- `selected_lot_ids = None` → all lots in backend scope
- explicit non-empty list → exactly those lots
- explicit unknown ids → `ValueError`

!!! note "Frontend empty-selection convention"

    UI state uses different semantics: empty selection means **all visible lots**, not "none".

    `LotsAnalysisPanel.svelte` implements that by expanding empty UI selection into
    `effectiveSelectionIds = visibleLots.map((lot) => lot.lot_id)` before lot-scoped requests.

    So if you call API directly, send `null`/omit field for "all lots", or send explicit visible IDs
    for "all visible lots after frontend filtering". Do **not** assume raw `[]` automatically means all.

Also note: `PERFORMANCE_HISTORY` ignores lot selection entirely by schema/implementation.

---

## 📈 WAC Lines {: #wac-lines }

`BROKER_WAC_HISTORY` and `CUMULATIVE_WAC_HISTORY` come from LibreFolio's single average-cost implementation, `compute_average_costs()` (see [WAC & Cost Basis](wac.md)). The lines are computed only when one of the two analyses is requested.

`_compute_average_cost_lines()` maps the loaded asset transactions (ordered by date, then id) with `cost_movement_from_transaction()` — split-linked adjustments become splits — and makes **one** call for all the lines:

| Line key | Movements | Feeds |
|----------|-----------|-------|
| Broker id | That broker's movements | `broker_wac_history` (`BrokerWACHistoryPoint`) |
| `"__all__"` (`ALL_BROKERS`) | Every broker in scope, pooled: a transfer between two brokers in scope leaves at the pool's average and comes back in at its cost basis | `cumulative_wac_history` (`CumulativeWACHistoryPoint`) |

The report currency is the analysis `target_currency`, with `asset_leg=False`. Each acquisition is converted at its own date; quantities are the brokers' own, with no owner share applied.

`average_cost_points(line, history_dates)` (`financial_math/lots/average_cost_lines.py`) emits `(date, wac, pool_qty)` for each history date from the line's first movement on, reading `line.state_at(date)`: `wac` is `unit_cost_report` (per single unit, in the target currency), `pool_qty` the pool's quantity. **A date on which the pool lacks part of its cost has no point** — a missing conversion or an acquisition without cost basis — so the chart shows a gap rather than a wrong average. `trim_dates()` then cuts the points to the displayed range.

`_report_gaps(data_quality, lines, conversion_gaps, target_currency, asset)` puts in the response what the lines could not compute, merged with every other conversion the analysis could not make (`conversion_gaps = fx_resolver.missing_pairs()`, see [FX Conversion](#fx-conversion)). It runs once, after every builder, through the same `build_data_quality_report()` (`financial_math/portfolio/data_quality.py`) as the Dashboard banner:

- **Missing conversions** (the lines' report leg plus `conversion_gaps`): `data_quality.missing_fx_pairs` receives one `WACMissingPairInfo(pair, dates)` per pair, its dates merged across sources, and `data_quality.issues` the `MISSING_FX_MARKET` / `MISSING_FX_RATES` issues derived from them, given the configured and real-provider pair sets of `load_configured_fx_pair_sets()`;
- **Acquisitions of unknown cost** (`unknown_cost_movement_ids` on any line): one `MISSING_COST_BASIS` issue for the analysed asset, built with `missing_cost_basis_assets=[(asset.id, asset.display_name)]` — the same issue as the portfolio banner;
- `calculation_status` turns from `COMPLETE` to `DEGRADED` when a line misses a rate or a cost basis, **or** any other conversion of the analysis is missing: the gap is isolable.

In the panel, the issues appear in `LotDataQualityBanner`, grouped by code and without call-to-action buttons.

---

## 🕰️ History Builders

Key builders — in the service:

- `_build_lot_summaries()` — scalar lot rows for table/modal
- `_build_gantt_segments()` — custody fragments
- `_build_lot_event_rows()` — full lot chronology

and in `financial_math/lots/`:

- `build_value_history()` — continues closed lots to `date_to` via `lot_history_end_date(..., extend_closed=True)`, unless a rate is missing (see [FX Conversion](#fx-conversion)); values a still-open LONG lot at cost up to `at_cost_until` (see [Estimated-at-Cost Fallback](#estimated-at-cost-fallback))
- `build_return_history()` — same continuity and at-cost rules, plus `relative_return` against `opening_reference_price()` (see [Reference Price](#reference-price))
- `build_price_history()` — truncates at closure date, no post-close points
- `build_broker_wac_history()` / `build_cumulative_wac_history()` — WAC points read from the average-cost lines via `average_cost_points()` (see [WAC Lines](#wac-lines))
- `build_performance_history()` — asset-wide ROI/TWRR from NAV + external cash flows. The NAV is read only on a day with a mark: no at-cost fallback reaches it (see [Estimated-at-Cost Fallback](#estimated-at-cost-fallback)). Money in: a BUY's amount and an ADJUSTMENT-in's money. Money out: a LONG SELL closure's proceeds and, for an ADJUSTMENT-out carrying a cost basis, the cost it hands over — `|quantity| × cost_basis_override`, converted from `cost_basis_currency` (the asset's currency when empty) at the row's date; the flow is read from the row, never from the `ADJUSTMENT_OUT` closures' proceeds. Transfer legs crossing the broker scope count at market value: a pair the re-run over the accessible brokers holds whole, and a leg read at the scope's edge (see [Transfers Across the Scope's Edge](#scope-edge-transfers)). An ADJUSTMENT-out without a cost basis is a quantity correction, never a flow. The units of an ADJUSTMENT-out leave at cost, so on a day the asset is quoted above that cost the gain they carried leaves with them — the same principle as an ADJUSTMENT-in valued at cost.

Important nuance: `date_from` trims emitted rows only. Engine still starts from earliest in-scope asset transaction so FIFO state stays correct.

---

## 🔗 Related

- 🧠 **[FIFO Lot Engine](fifo_lot_engine.md)** — Pure event-sourced FIFO core
- 🧮 **[Financial Math Layer](../financial_math.md)** — The layer `financial_math/lots/` belongs to: rules, package map, guards
- ⚖️ **[WAC & Cost Basis](wac.md)** — The average-cost function behind the WAC lines
- 📖 **[FIFO Lot Analysis Theory](../../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)** — Financial interpretation of lot metrics
- 🖥️ **[Lots Analysis Frontend](../../frontend/components/features/lots-analysis.md)** — `LotsAnalysisPanel` and chart/table consumers
