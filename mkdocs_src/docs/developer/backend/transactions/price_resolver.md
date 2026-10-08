# 📈 Price Resolver — the single valuation-mark source

`backend/app/services/price_resolver.py` answers the one question every engine needs —
*what is the per-unit mark of asset X on day D?* — with a single coherent daily model, so
charts, valuation (NAV) and metrics (MWRR/TWRR/ROI) all read from the **same** numbers.

Since the legacy valuation engine was removed (1.1 dev cycle), the resolver is **the only
valuation path**: there is no market-only fallback cascade and no transition flag. If a value
reaches a report, it came through here.

## 🪜 The daily model

Per asset, per day `D`, `AssetPriceSeries.resolve(D)` returns a `ResolvedMark` whose `source`
is decided by a four-tier ladder:

| Tier | `MarkSource` | Meaning |
|------|--------------|---------|
| 1 | `MARKET` | An asset-system price (`price_history.close`) exists on `D` — the exact real quote |
| 2 | `TRADE_AVG` | No quote, but same-day transactions exist — average of their unit prices |
| 3 | `CARRIED` | Otherwise, the last observation ≤ `D` carried forward (LOCF; market- or trade-origin) |
| 4 | `MISSING` | Nothing on or before `D` — `unit_price = 0`, `currency = None` |

Construction collapses the observation stream to **one value per day** first: a MARKET quote
wins the day; otherwise same-day TRADE observations are averaged. Queries are O(log n) via
`bisect`.

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

Only `portfolio_engine.py` passes it, and only for a calculation run with `include_candles=True`,
which `POST /api/v1/portfolio/report` requests through `include_pnl_candles`. The Growth chart asks
for it lazily — when the user switches to the P&L **Candles** submode and no candles are loaded yet —
on the Dashboard and on a broker page (see the
[Portfolio Growth Chart](../../../user/dashboard/charts.md#portfolio-growth-chart)).
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
  mirrors the `_FxRateResolver` load-once / query-sync shape.
- **Native currency, market ×`quote_base_quantity` scale — conversion belongs to the engine.**
  Every observation stays in its own native currency; each `ResolvedMark` carries that
  `currency` so the consuming engine converts to the reporting currency **at the valuation
  date** (a carried mark must translate at the day it is read — otherwise a foreign holding
  freezes a stale FX). Trade unit prices are lifted to the qbq axis (`× quote_base_quantity`)
  so a qbq=100 bond lands on its ~100 par axis alongside market quotes. The portfolio engine
  takes those rates from `fx_rate_map`, preloaded once per calculation by `_preload_fx_rates()`
  with a single `convert_bulk()` call — see
  [FX Architecture](../fx/architecture.md#convert-bulk-window) for how that call loads only the
  rate window it can use.
- **Never for realized / cost basis.** The mark is for *open-position valuation* and the price
  line only. Realized P&L and cost basis always come from the actual transaction prices, never
  from this estimate.
- **What feeds it** (`build_asset_price_series`): MARKET observations from `price_rows`
  (`(date, close, currency)`; `close` is already per-qbq and is not re-scaled), with their
  optional intraday range from `ohlc_by_date`, TRADE observations from BUY/SELL
  (`|amount| / |quantity|` in the transaction currency) and priced ADJUSTMENT carryovers
  (`cost_basis_override`). Split-linked rows and pure quantity adjustments carry no price and
  are skipped.

## 🔌 Who consumes it

Exactly two modules import the resolver today:

| Consumer | What it uses it for |
|----------|---------------------|
| `portfolio_engine.py` | The daily valuation brain: one `AssetPriceSeries` per held asset feeds the daily portfolio states → NAV snapshots → ROI/TWRR/MWRR (via `roi_utils`) and the value/P&L history lines; on request, also the synthetic P&L candles (with `ohlc_by_date`) |
| `lots_analysis_service.py` | qbq-aware lot valuations, `market_prices` / `estimated_market_prices` maps, performance NAV — see [Lots Analysis Service](lots_analysis_service.md) |

Everything downstream (dashboard KPIs, portfolio/broker reports, AI Export valuation sections)
reads numbers these two produced, which is what makes the resolver the single source: a change
here moves every chart and every metric together.
