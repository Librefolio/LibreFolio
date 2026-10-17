# 📈 Price Resolver — the single valuation-mark source

`backend/app/services/financial_math/price_marks.py` answers the one question every engine needs —
*what is the per-unit mark of asset X on day D?* — with a single coherent daily model, so
charts, valuation (NAV) and metrics (MWRR/TWRR/ROI) all read from the **same** numbers. The
module belongs to the [financial math layer](../financial_math.md).

Since the legacy valuation engine was removed (1.1 dev cycle), the resolver is **the only
valuation path**: there is no market-only fallback cascade and no transition flag. If a price
reaches a report, it came through here; a holding the resolver cannot mark at all is counted at
its book cost, never at a price (see [No observation: valued at cost](#valued-at-cost)).

## 🪜 The daily model

Per asset, per day `D`, `AssetPriceSeries.resolve(D)` returns a `ResolvedMark` whose `source`
is decided by a four-tier ladder:

| Tier | `MarkSource` | Meaning |
|------|--------------|---------|
| 1 | `MARKET` | An asset-system price (`price_history.close`) exists on `D` — the exact real quote |
| 2 | `TRADE_AVG` | No quote, but same-day `BUY`/`SELL` rows exist — average of their unit prices |
| 3 | `CARRIED` | Otherwise, the last observation ≤ `D` carried forward (LOCF; market- or trade-origin) |
| 4 | `MISSING` | Nothing on or before `D` — `unit_price = 0`, `currency = None` |

Construction collapses the observation stream to **one value per day** first: a MARKET quote
wins the day; otherwise same-day TRADE observations are averaged. Queries are O(log n) via
`bisect`.

`MISSING` is the resolver's last word, not the holding's: the portfolio engine counts a held
position of known cost at that cost instead — see [No observation: valued at cost](#valued-at-cost).

## 📏 Staleness and the `estimated` flag

Two orthogonal flags ride on every mark — do not conflate them:

- **`price_backward_fill`** — `None` for an exact same-day observation; a `BackwardFillInfo`
  (`actual_rate_date` + `days_back`) when the value was carried forward. This is the
  project-wide staleness contract FX and asset pricing already expose, so the frontend renders
  the "value fades with age" line for free.
- **`estimated`** — `True` whenever the value did **not** come from a real asset-system quote
  (i.e. it is TRADE-derived), *independently of freshness*. A real quote carried forward is
  **stale but not estimated**; a fresh trade mark is estimated but not stale.

## 🕯️ Intraday range: `open` / `high` / `low`

`PriceObservation` and `ResolvedMark` carry three optional fields, `open`, `high` and `low`, on the
same market ×`quote_base_quantity` scale as the close. They are filled only on an **exact `MARKET`
day whose `price_history` row has all three**; everywhere else they are `None`:

| Mark | `open` / `high` / `low` |
|------|-------------------------|
| `MARKET`, full triple in `price_history` | The row's values |
| `MARKET`, one or two of the three missing | `None` — a partial triple counts as no range; an extremum is never guessed |
| `TRADE_AVG` | `None` — a trade has one unit price, no intraday range |
| `CARRIED` | `None` — nothing traded that day, and the range of an earlier day is never carried forward |
| `MISSING` | `None` |

`latest()` never carries a range either.

The range enters through `build_asset_price_series(ohlc_by_date=…)`: an optional map
`date → (open, high, low)` for MARKET days already present in `price_rows`. It is a separate
argument, not a wider `price_rows` tuple, so the other caller (`lots_analysis_service.py`) keeps the
`(date, close, currency)` shape; a day left out of the map has no range.

Only the portfolio engine (`financial_math/portfolio/engine.py`) passes it, and only for a calculation run with `include_candles=True`,
which `POST /api/v1/portfolio/report` requests through `include_pnl_candles`. The Growth chart asks
for it lazily — when the user switches to the P&L **Candles** submode and no candles are loaded yet —
on the Dashboard and on a broker page (see the
[Portfolio Growth Chart](../../../user/dashboard/charts.md#portfolio-growth-chart)); a failed
request is asked again at most three times, 2, 4 and 8 s later
([Lazy sections after a failure](../../frontend/state/domain-state.md#lazy-report-retry)).
The engine builds the map from the `price_history` rows it already loads, with no extra query, and
composes one synthetic P&L candle per day:

- each held asset with a range contributes its value at `open`, `high` and `low`; an asset without
  one contributes a flat value (open = high = low = close);
- `offset = total_pnl − Σ close`, and the candle is `offset + Σ open`, `offset + Σ high`,
  `offset + Σ low`, closing at `total_pnl`, the day's total P&L — the offset absorbs cash, the
  capital baseline and in-transit value;
- a day on which any held asset is `MISSING` gets no candle at all.

## 🧊 Design contract

- **Two layers.** `AssetPriceSeries` is a *pure, synchronous, immutable* calculator built from
  pre-normalized observations — no I/O, no DB, no async, no FX — so engines (themselves pure)
  can query it and trust it blindly. Data acquisition happens once per calculation in the async
  caller, which then feeds normalized observations via `build_asset_price_series()`. This
  mirrors the load-once / query-sync shape of `FxRateResolver` (`financial_math/lots/conversions.py`).
- **Native currency, market ×`quote_base_quantity` scale — conversion belongs to the engine.**
  Every observation stays in its own native currency; each `ResolvedMark` carries that
  `currency` so the consuming engine converts to the reporting currency **at the valuation
  date** (a carried mark must translate at the day it is read — otherwise a foreign holding
  freezes a stale FX). Trade unit prices are lifted to the qbq axis (`× quote_base_quantity`)
  so a qbq=100 bond lands on its ~100 par axis alongside market quotes. The portfolio engine
  takes those rates from `fx_rate_map`, preloaded once per calculation by `_preload_fx_rates()`
  (`financial_math/portfolio/engine.py`) with a single `convert_bulk()` call — see
  [FX Architecture](../fx/architecture.md#convert-bulk-window) for how that call loads only the
  rate window it can use.
- **Never for realized / cost basis.** The mark is for *open-position valuation* and the price
  line only. Realized P&L and cost basis always come from the actual transaction prices, never
  from this estimate.
- **What feeds it** (`build_asset_price_series`): MARKET observations from `price_rows`
  (`(date, close, currency)`; `close` is already per-qbq and is not re-scaled), with their
  optional intraday range from `ohlc_by_date`, and TRADE observations from `BUY`/`SELL` rows
  with an amount (`|amount| / |quantity|` in the transaction currency). Split-linked rows are
  skipped.
- **An `ADJUSTMENT` is never a price**, incoming or outgoing, with or without a cost basis
  (developer decision P2): its `cost_basis_override` is a cost — often the position's average
  cost — not what the asset was worth that day. So is the one that takes units out at the Auto
  cost of its own broker, as a broker deletion, a split of a `TRANSFER` pair or the
  [lone giving legs step](../../architecture/database/index.md#lone-transfer-legs) writes it
  (decision 47). Only market quotes and `BUY`/`SELL` trades mark an asset.

## 🧾 No observation: valued at cost {: #valued-at-cost }

When the series has nothing on or before the day, the portfolio engine does not leave a held
position unvalued if its cost is known. `DailyStateBuilder._value_held_position()`
(`financial_math/portfolio/daily_state.py`) asks `_market_value_for()` first; on a `MISSING`
answer, a position whose average-cost pool is complete in the report currency
(`CostStep.report_complete`) counts at its book cost, `cost_report_for(qty)` — each acquisition
converted at its own date, never at the valuation date. That is a declared estimate, not a price
(developer decision, option A):

| `ValuationResult` field | Value at cost |
|-------------------------|---------------|
| `source` | `ValuationSource.ESTIMATED_AT_COST` |
| `market_value` | The book cost of the held quantity, in the report currency |
| `effective_unit_price` / `effective_currency` | `None` — no price is reported |
| `reference_date` / `reference_unit_price` / `reference_currency` | `None` |
| `stale`, `missing_fx_pair` | `False`, `None` — no price ages and no rate is read |

The position is not missing, so the day's NAV stays complete and its synthetic P&L candle is not
dropped (the cost counts as a flat value). Its unrealized result is zero:
`_add_unrealized_part(..., at_cost=True)` adds nothing to the unrealized split, neither an asset
nor an exchange-rate part (see [WAC & Cost Basis](wac.md#unrealized-split)). With its cost
unknown or incomplete, the position stays `MISSING` and is left out of the NAV. A missing
exchange rate on a mark that exists is not this case: the mark is there, only its conversion
fails.

The choice is made day by day, with no look-ahead: the cost stands in only on the days before the
asset's first observation. From the first quote, `BUY` or `SELL` on, the resolver always has a
mark — carried forward when it is old, and flagged stale past `STALE_PRICE_THRESHOLD_DAYS` — and
the price wins.

A cost stands in wherever the engine needs the value of a security with no observation — the
book cost, except for units in transit, which keep the cost recorded on the transfer:

| Where | Value |
|-------|-------|
| Held position, daily and end-date snapshot (`_value_held_position()`) | The book cost of the held quantity |
| Orphan `TRANSFER` leg (`_transfer_leg_capital()`) | The cost the leg moves in its pool (`step.cost_report_change`): the cost it adds, or the average cost it removes — the capital follows the pool's book cost both ways, as for an incoming in-kind `ADJUSTMENT` (an outgoing one takes out the value it hands over instead). An unknown cost counts as zero, the pool's own convention. While the pool's cost is complete the leg is neutral, the holding being valued at that same cost; with the pool's cost incomplete the holding is `MISSING`, yet the leg still moves its known cost, so nothing is left in capital once the units are gone |
| Internal `TRANSFER` pair between two brokers (`_internal_pair_value()`) | The book cost the arrival adds to the receiver's pool (`_movement_cost_step()` of the receiving leg: the cost recorded on that leg, converted at its date), rescaled from the receiver's share to the sender's, whether or not the receiver's pool is complete; an arrival of unknown cost adds 0, so there is no flow. With the receiver's pool complete, that is what its NAV takes the units at. With it incomplete, the receiver's holding is `MISSING`: the receiver's line takes the gap — its own unknown cost, with the NAV incomplete — and the sender's line is the same as with a complete pool |
| Units in transit (`_compute_in_transit()`) | The cost recorded on the transfer, converted at the arrival date |

The holding's valuation hierarchy is therefore `MARKET_PRICE` (a quote, exact or carried) >
`LAST_TRADE_PRICE` (the last `BUY`/`SELL`, carried) > `ESTIMATED_AT_COST` > `MISSING`. The
Dashboard warns about the at-cost positions of assets with a provider with `VALUED_AT_COST`, more
than 14 days after the asset's first acquisition
(see [Data Quality Banner](../../frontend/data-quality-banner.md#active-issuecodes)). The lots
analysis follows the same day-by-day rule: it values an open LONG lot at its cost on every day
with no observation on or before it, and its own warning, `CURRENT_PRICE_ASSUMED_AT_COST`, names
those days — see [Lots Analysis Service](lots_analysis_service.md#estimated-at-cost-fallback).

## 🔌 Who consumes it

Two consumers use the resolver today:

| Consumer | What it uses it for |
|----------|---------------------|
| Portfolio engine (`financial_math/portfolio/`) | The daily valuation brain: `engine.py` builds one `AssetPriceSeries` per held asset, and `DailyStateBuilder` (`daily_state.py`) reads it to build the daily portfolio states → NAV snapshots → ROI/TWRR/MWRR (`financial_math/returns.py`) and the value/P&L history lines; on request, also the synthetic P&L candles (with `ohlc_by_date`) |
| `lots_analysis_service.py` | One series per analysis, built before the FIFO engine runs: the reference price of a lot opened by an `ADJUSTMENT` (its mark on the opening day), the days valued at cost (`last_day_without_observation()`), then the qbq-aware lot valuations, the `market_prices` / `estimated_market_prices` maps and the performance NAV — see [Lots Analysis Service](lots_analysis_service.md#unified-price-resolver) |

Everything downstream (dashboard KPIs, portfolio/broker reports, AI Export valuation sections)
reads numbers these two produced, which is what makes the resolver the single source: a change
here moves every chart and every metric together.
