# LibreFolio Dashboard — Formula/Source Report

## Table of contents

1. [Scope, data flow, and percentage conventions](#scope-data-flow-and-percentage-conventions)
2. [Key distinctions to understand first](#key-distinctions-to-understand-first)
3. [Dashboard KPI cards](#dashboard-kpi-cards)
   1. [Period P&L card](#period-pl-card)
   2. [Returns card](#returns-card)
   3. [Net Worth card](#net-worth-card)
4. [Growth chart](#growth-chart)
   1. [What backend path actually feeds it](#what-backend-path-actually-feeds-it)
   2. [ABS mode](#abs-mode)
   3. [% mode](#pct-mode)
5. [Allocation panel](#allocation-panel)
   1. [Current Type tab](#current-type-tab)
   2. [Current Sector tab](#current-sector-tab)
   3. [Current Geo tab](#current-geo-tab)
   4. [History view](#history-view)
6. [Positions panel](#positions-panel)
   1. [View/mode matrix](#viewmode-matrix)
   2. [Backend period-attribution formulas (`get_positions_contribution`)](#backend-period-attribution-formulas-get_positions_contribution)
   3. [Exposure / Table / OPEN](#exposure--table--open)
   4. [Exposure / Table / CLOSED](#exposure--table--closed)
   5. [Contribution / Table](#contribution--table)
   6. [Exposure / Map](#exposure--map)
   7. [Contribution / Map](#contribution--map)
7. [Recent Transactions panel](#recent-transactions-panel)
8. [Data quality banner (when visible)](#data-quality-banner-when-visible)
9. [High-value reconciliation caveats](#high-value-reconciliation-caveats)

---

## Scope, data flow, and percentage conventions

### Dashboard data flow actually used by `+page.svelte`

- Main dashboard load path: `frontend/src/routes/(app)/dashboard/+page.svelte` → `fetchReport()` in `frontend/src/lib/stores/portfolio/portfolioStore.svelte.ts`.
- `fetchReport()` calls `POST /api/v1/portfolio/report` with:
  - `include_summary = true`
  - `include_history = true`
  - `include_allocation_history = true`
  - `include_positions_contribution = false` normally, `true` only when Contribution mode or Closed filter needs it.
- Backend unified report path: `backend/app/services/portfolio_service.py#get_report()`.
- Backend aggregate engine path: `PortfolioCalculationEngine.calculate()` in `backend/app/services/portfolio_engine.py`, then `DerivedViewsBuilder` for history/allocation/performance views.

### Important source-of-truth split

There are **two different backend sources** feeding different dashboard widgets:

1. **Engine-based aggregate/time-series views** (date-range-aware):
   - KPI cards (`summary.*` except `summary.holdings`)
   - Growth chart (`history[*]`)
   - Allocation panel (`summary.allocation_by_*`, `allocation_history.*`)

2. **Service holdings loop** (`summary.holdings`) used by Exposure OPEN views:
   - Exposure table/open
   - Exposure treemap/open

These are **not the same valuation path**.

### Currency convention

- Most dashboard money values are already converted server-side into the selected dashboard currency (`target_currency` / `displayCurrency`).
- Exception: **Recent Transactions → Cash** stays in each transaction’s own stored `tx.cash.code` currency.

### Percentage convention

Not all backend percentage-ish fields have the same unit.

- **Already 0–100 in backend**:
  - `holding.nav_weight_percent`
  - `summary.allocation_by_*[*].value`
  - `allocation_history.*.components[*].value`

- **Ratio/decimal in backend, multiplied by 100 in frontend for display**:
  - `holding.price_change_1d`
  - `holding.gain_loss_percent`
  - `position.period_pnl_percent`
  - `summary.simple_roi_percent`
  - `summary.twrr_percent`
  - `summary.mwrr_annualized_percent`
  - `summary.mwrr_cumulative_percent`
  - `history[*].twrr`
  - `history[*].mwrr_annualized`
  - `history[*].mwrr_cumulative`
  - `history[*].roi`

### Legacy helper note

`backend/app/services/portfolio_service.py` still contains legacy `_HistoryTxRow`, `_HistoryCalcPoint`, and `_build_history_series()`, but **Dashboard Home does not use that path anymore**. Dashboard Home uses `get_report()` → engine daily states → `get_history()` / `DerivedViewsBuilder.build_history()`.

---

## Key distinctions to understand first

1. **“Unrealized P&L” and “Period P&L” are different kinds of numbers.**
   - Open Exposure views use lifetime/current unrealized values (`holding.gain_loss`).
   - Contribution views and Closed Exposure views use period attribution (`period_pnl`).

2. **Open Exposure views are not end-of-period snapshots.**
   - `summary.holdings` is built with `today = date.today()`, `latest price ever`, and all-time current quantities.
   - So OPEN Exposure values/weights/1D change/unrealized numbers are effectively **today/current-position metrics**, even when dashboard date range ends in the past.

3. **Contribution/closed views are date-range-aware; open Exposure views mix time bases.**
   - Contribution data comes from `get_positions_contribution(date_from, date_to)`.
   - OPEN Exposure merges current holdings fields with period-scoped realized/cost fields.

4. **Exposure-table “Realized” is not realized-sales-only in current code.**
   - `ExposureTable.svelte#getRealizedAmount()` returns:
     - `period_realized_gain_loss + period_income`
   - Header/tooltip still say “Realized / Realized Sales”, but code adds income.

5. **Treemap semantics differ completely by mode.**
   - Exposure treemap: **area = current holding value**, **color = unrealized return %**.
   - Contribution treemap: **area = abs(period_pnl)**, **color = fixed green/red by sign**.

6. **Allocation panels are engine-based and date-range-aware.**
   - They use end-of-range / per-day engine states, not `summary.holdings`.

7. **Recent Transactions ignores date range.**
   - It respects broker filter and limit, but not dashboard `dateFrom/dateTo`.

---

## Dashboard KPI cards

## Period P&L card

Source path:
- Frontend: `frontend/src/routes/(app)/dashboard/+page.svelte` (`periodPnl*`, `uglDelta*`, `realized*`, `income*`, `fees*`)
- Backend summary builder: `backend/app/services/portfolio_service.py#get_summary()`

| Name shown in UI | What it represents | Exact formula / computation | Source | Notes / caveats |
|---|---|---|---|---|
| `Period P&L` | Total profit/loss attributable to selected period after external cash-flow adjustment | `summary.period_pnl = nav_end - nav_start - period_net_flows` where `nav_end = summary.net_worth.amount = last_state.nav_value`; `nav_start = NAV at or before date_from` (or `0` for full history); `period_net_flows = sum(external_cash_flow within period)` | `summary.period_pnl` from `PortfolioService.get_summary()` | This is **period-scoped**. Not lifetime. Hidden backend residual `period_other_result` can make hero differ from visible sub-bars. |
| Daily delta under hero (`kpi-pnl-delta-day`) | Day-over-day change in cumulative total P&L | `pnlDeltaDay = lastHistory.total_pnl - prevHistory.total_pnl` | Client-side from `history[-1].total_pnl` and `history[-2].total_pnl` | Uses last 2 history points in displayed range. Not same metric as `summary.period_pnl`, but related. |
| `Unrealized Delta` | Change in unrealized gain/loss of open holdings over selected period | `summary.period_unrealized_gain_loss_delta = (end_market_value - end_open_cost_basis) - (start_market_value - start_open_cost_basis)` | `summary.period_unrealized_gain_loss_delta` | Uses `market_value - open_cost_basis`, **not** full `nav - book`. So it excludes cash and excludes the full in-transit/book-value story. |
| `Realized Sales` | WAC-based realized gain/loss from sells in period | `summary.period_realized_gain_loss = Σ(sell_proceeds_base - sell_qty × WAC_before_sell_base)` over `SELL` with `date_from < tx.date <= date_to` | `summary.period_realized_gain_loss` | Sell proceeds use absolute sale amount converted to base at `tx.date`. Cost basis uses WAC just before the sell. |
| `Income` | Period income from dividends and interest | `summary.period_income = Σ abs(amount_base)` over `DIVIDEND` and `INTEREST` with same date filter | `summary.period_income` | Positive number in backend and UI. |
| `Fees & Taxes` | Period drag from fees and taxes | `summary.period_fees_taxes = Σ abs(amount_base)` over `FEE` and `TAX` with same date filter | `summary.period_fees_taxes` | Backend stores positive magnitude; frontend displays it as negative by prepending `-`. Tooltip splits `summary.period_fees` and `summary.period_taxes`, also displayed negative. |
| Component bars | Purely relative visual bars for breakdown rows | `barPct = abs(component_value) / max(abs(uglDelta), abs(realized), abs(income), fees) × 100` | Client-side `pnlBarMax`, `pnlBarPct()` | Bars do **not** sum to 100. They show relative magnitude inside this card only. |

**Important hidden residual:**

Backend also computes:

- `summary.period_other_result = period_pnl - unrealized_delta - realized - income + fees_taxes`

That value is **not rendered anywhere** in the KPI card. So visible rows may not perfectly reconcile to the hero amount if `period_other_result != 0`.

---

## Returns card

Source path:
- Frontend: `frontend/src/routes/(app)/dashboard/+page.svelte` (`roiVal`, `twrrCumVal`, `mwrrCumVal`, `mwrrAnnVal`, `timingEffectVal`)
- Backend performance math: `backend/app/services/portfolio_service.py#get_summary()` + `backend/app/utils/financial/roi_utils.py`

| Name shown in UI | What it represents | Exact formula / computation | Source | Notes / caveats |
|---|---|---|---|---|
| Hero `Timing Effect` | Difference between investor-experience return and strategy-only return | `timingEffectVal_pp = (summary.mwrr_cumulative_percent - summary.twrr_percent) × 100` | Client-side from `summary.mwrr_cumulative_percent` and `summary.twrr_percent` | Units are **percentage points (pp)**, not %. Positive means investor timing helped relative to TWRR. |
| Small `%` under hero (`kpi-returns-delta-pct`) | Last day’s P&L change expressed as % of previous-day NAV | `pnlDeltaDayPct = (pnlDeltaDay / prevHistory.nav_value) × 100` | Client-side from history | Despite living in Returns card, this is **not** daily change of TWRR/MWRR/ROI. |
| `ROI` | Simple return over period relative to invested capital for that period | Backend builds `period_cfs` (actual external flows plus synthetic start cash flow `-period_start_nav` when needed); `period_net_invested = Σ(-cf.amount)`; then `simple_roi = (nav_end - period_net_invested) / period_net_invested` if `period_net_invested > 0`, else `0` | `summary.simple_roi_percent` | Frontend shows `summary.simple_roi_percent × 100`. If `date_from` set and starting NAV > 0, this is effectively `period_pnl / (nav_start + net_flows)`. |
| `TWRR Cum` | Cumulative time-weighted return for selected period | For each consecutive NAV snapshot pair: `V_start = nav[i-1]`; `V_end = nav[i]`; `CF_i = external cash flow on snapshot date using investor sign (deposit < 0, withdrawal > 0)`; `V_end_preCF = V_end + CF_i`; if `V_start != 0`, `HPR_i = (V_end_preCF - V_start) / V_start`; then `TWRR = Π(1 + HPR_i) - 1` | `summary.twrr_percent` via `calculate_twrr()` | Frontend shows `× 100`. Backend inserts synthetic start cash flow `-period_start_nav` when a mid-history period is requested so the metric is rebased to the selected period. |
| `MWRR Cum` | Cumulative money-weighted return for selected period | `mwrr_cumulative = (1 + mwrr_annualized)^(days/365) - 1` | `summary.mwrr_cumulative_percent` via `annualized_to_cumulative()` | Frontend shows `× 100`. |
| `MWRR Ann` | Annualized money-weighted return / XIRR | Solve for `r` in: `-initial_nav + Σ(CF_d / (1+r)^(d/365)) + (final_nav + CF_T) / (1+r)^(T/365) = 0`, using SciPy Newton. Deposits are negative CFs; withdrawals positive. `initial_nav = period_start_nav` if `>0`, else first actual NAV snapshot in period. | `summary.mwrr_annualized_percent` via `calculate_mwrr()` | Frontend shows `× 100`. This is annualized; cumulative value is separate row. |
| Return bars | Relative visual magnitude of displayed return metrics | `barPct = abs(metric) / max(abs(ROI), abs(TWRR Cum), abs(MWRR Cum), abs(MWRR Ann)) × 100` | Client-side `retBarMax`, `retBarPct()` | Visual only. Not additive. |

**Timing-effect styling only:**
- Label = neutral if `abs(timingEffectVal_pp) < 0.05`, else favorable/unfavorable by sign.
- Color intensity = `min(abs(timingEffectVal_pp) / 3, 1)`.
- This opacity/intensity is presentation only.

---

## Net Worth card

Source path:
- Frontend: `frontend/src/routes/(app)/dashboard/+page.svelte`
- Backend engine-derived summary fields: `PortfolioService.get_summary()` using `last_state` from `PortfolioCalculationEngine`

| Name shown in UI | What it represents | Exact formula / computation | Source | Notes / caveats |
|---|---|---|---|---|
| Hero `Net Worth` | End-of-range portfolio NAV | `summary.net_worth = last_state.nav_value = last_state.broker_nav_value + last_state.in_transit_market_value = (market_value + cash_value) + (in_transit_cash_value + in_transit_asset_market_value)` | `summary.net_worth` | This is engine-based and **date-range-aware** (`date_to` if selected, else today). |
| Daily delta under hero (`kpi-nav-delta-day`) | Day-over-day change in NAV | `navDeltaDay = lastHistory.nav_value - prevHistory.nav_value` | Client-side from last 2 history points | Uses displayed history range. |
| `Market Value` | End-of-range mark-to-market value of currently held assets in engine view | `summary.market_value = Σ asset_mv(dt_end)` over positive-qty positions, where `asset_mv` uses engine valuation hierarchy: `PriceHistory on/before dt_end` → else `last_buy_price <= dt_end` → else excluded. `compute_holding_value(qty, raw_price, quote_base_quantity) = (qty / quote_base_quantity_norm) × raw_price`; FX uses rate at `dt_end`. | `summary.market_value` from `last_state.market_value` | Excludes cash. Also excludes assets with no valuation source. Does **not** equal OPEN Exposure-table Value column in all cases. |
| Market bar marker | Start-of-period reference for Market Value bar | `marker = summary.period_market_value_start / nwBarMax × 100` | `summary.period_market_value_start` | This marker is a proper same-family comparison (market value start vs market value end). |
| `Book Value` (label shown) | **Actually current open cost basis only**, not full book value | UI uses `summary.open_cost_basis`, where `open_cost_basis = Σ(WAC_dt_end × qty)` converted to target currency at `dt_end` FX | `summary.open_cost_basis` | Label says “Book Value”, but rendered number is **not** `summary.book_value`. It excludes cash and excludes in-transit book value. |
| Book bar marker | Start-of-period proxy marker under the “Book Value” bar | UI uses `summary.period_book_value_start` as proxy because start-of-period `open_cost_basis` is not exposed separately | `summary.period_book_value_start` | This is **not apples-to-apples** with current `summary.open_cost_basis`. Marker includes full book value (cash + in-transit book value), while current bar shows only open cost basis. |
| `Cash Value` | End-of-range on-broker cash only | `summary.cash_total = last_state.cash_value` | `summary.cash_total` | Excludes in-transit cash. Tooltip splits it into contributed-capital cash vs generated-returns cash using history last point. |
| Cash tooltip: `Cash from Contributed Capital` | Portion of cash attributed to undeployed external capital | Let `cash_like = cumulative_cash + in_transit_cash`; `capital_cash_pool_total = ΣK[broker]`; `returns_cash_pool_total = ΣR[broker]`; `pool_sum = capital_cash_pool_total + returns_cash_pool_total`. If `pool_sum > 0` and `abs(pool_sum - cash_like) > 0.01`: `scale = cash_like / pool_sum`; `cash_from_contributed = max(capital_cash_pool_total × scale, 0)`. Else: `cash_from_contributed = min(capital_cash_pool_total, cash_like)`. | `history[-1].cash_from_contributed_capital` | Used only in GrowthChart / cash tooltip. Not separately shown as card row. |
| Cash tooltip: `Cash from Generated Returns` | Portion of cash attributed to realized/income returns left in cash | If scaled branch used above: `cash_from_generated = max(cash_like - cash_from_contributed, 0)`; else same formula | `history[-1].cash_from_generated_returns` | Used only in tooltip. |
| `Net Deposited Capital` | Net external capital contribution in the selected period | `summary.net_deposited_capital = summary.total_deposited - summary.total_withdrawn` where `total_deposited = Σ abs(DEPOSIT amount_base)` in period and `total_withdrawn = Σ abs(WITHDRAWAL amount_base)` in period | `summary.net_deposited_capital`, `summary.total_deposited`, `summary.total_withdrawn` | **Period-scoped**, not lifetime, despite schema text sounding global. UI shows withdrawals with a minus sign only at render time. |
| Diverging deposit/withdraw bar | Relative display of gross deposits vs gross withdrawals | Right half width: `depositPct = totalDeposited / nwBarMax × 100`; left half width: `withdrawPct = totalWithdrawn / nwBarMax × 100` | Client-side from totals | Visual only. The displayed net number is `net_deposited_capital`; the halves are gross flows. |
| Net-worth card bar scale | Common scale for hero-related bars/markers | `nwBarMax = max(netWorthHero, marketValueStart, marketValueEnd, purchaseCostEnd, purchaseCostStartProxy, cashEnd, cashStart, totalDeposited, totalWithdrawn)` | Client-side `nwBarMax` | Means the deposit/withdraw bars are scaled against the same max as market/book/cash bars. |

**Cash-pool transaction rules used by GrowthChart/cash tooltip**

Per broker, engine tracks:
- `K` = capital pool
- `R` = returns pool
- `W` = withdrawn-returns pool (global)

Updates in daily engine loop:
- **DEPOSIT `amt`**: `restore = min(amt, W)`; `R += restore`; `W -= restore`; `K += amt - restore`
- **WITHDRAWAL `amt`**: `from_k = min(amt, K)`; `K -= from_k`; `remaining = amt - from_k`; `from_r = min(remaining, R)`; `R -= from_r`; `W += from_r`
- **DIVIDEND / INTEREST `amt`**: `R += amt`
- **FEE / TAX `amt`**: `R -= amt`; if `R < 0`, then `K += R` and `R = 0`
- **BUY `amt`**: consume returns first: `from_r = min(amt, R)`; `R -= from_r`; `K -= (amt - from_r)`
- **SELL with proceeds `P` and cost basis `CB`**: `K += CB`; `R += (P - CB)`; if `R < 0`, shift deficit into `K` then clamp `R = 0`

---

## Growth chart

## What backend path actually feeds it

- Frontend component: `frontend/src/lib/components/dashboard/GrowthChart.svelte`
- Data prop: `history` from `portfolioStore.fetchReport()` / `PortfolioReport.history`
- Backend builder path:
  - `PortfolioService.get_report()`
  - `PortfolioService.get_history()`
  - `DerivedViewsBuilder.build_history()` for daily state values
  - `calculate_twrr_series()`, `calculate_simple_roi_series()`, `calculate_mwrr_series()` for `%` mode

**Important:** the old `_build_history_series()` helper is **not** what Dashboard Home uses here.

### History-series construction actually used

1. Engine computes dense `DailyPortfolioState[]` from inception (`date_from=None` in unified report) to `date_to`.
2. `get_history()` converts each daily state into a `PortfolioHistoryPoint`-compatible object.
3. If a dashboard `date_from` is selected:
   - backend still computes from inception,
   - rebases performance metrics using a synthetic start cash flow `-period_start_nav`,
   - then slices displayed history to `d >= date_from`.
4. Backend forcibly sets first visible point to:
   - `twrr = 0`
   - `mwrr_annualized = 0`
   - `mwrr_cumulative = 0`
   - `roi = 0`
   for chart continuity.

### ABS mode

| Series / number shown | What it represents | Exact formula / computation | Source | Notes / caveats |
|---|---|---|---|---|
| `NAV` line | Full portfolio NAV by day | `history[i].nav_value = broker_nav_value + in_transit_market_value` | `history[*].nav_value` | End-of-day daily engine snapshots. |
| `Capital Baseline` dashed line | Cumulative external capital contributed to the portfolio | `history[i].capital_baseline = daily_state.cumulative_external_cash_flow = Σ(deposits - withdrawals)` up to that day in target currency | `history[*].capital_baseline` | Same quantity as engine `capital_baseline`. |
| `Assets at Cost` stacked area | Asset-like book value (held assets + in-transit asset cost basis) | `history[i].book_asset_like = open_cost_basis + in_transit_asset_cost_basis` | `history[*].book_asset_like` | This is **cost basis**, not market value. |
| `Cash from Generated Returns` stacked area | Cash attributed to gains/income not currently invested | `history[i].cash_from_generated_returns` from 3-pool rules above | `history[*].cash_from_generated_returns` | Derived decomposition, not ledger balance type. |
| `Cash from Contributed Capital` stacked area | Cash attributed to undeployed external capital | `history[i].cash_from_contributed_capital` from 3-pool rules above | `history[*].cash_from_contributed_capital` | Derived decomposition. |
| Implied top of stacked areas | Total book value | `book_asset_like + cash_from_generated_returns + cash_from_contributed_capital = book_value` (subject to tiny scaling/rounding adjustment in cash split) | Derived from history fields | Book value itself is not plotted as separate line, but this stacked top is that concept. |
| Gap between `NAV` and `Capital Baseline` | Total P&L vs external capital baseline | `history[i].total_pnl = history[i].nav_value - history[i].capital_baseline` | `history[*].total_pnl` | Tooltip shows this explicitly. Chart does not separately plot a “Total P&L” series line. |

### % mode

| Series / number shown | What it represents | Exact formula / computation | Source | Notes / caveats |
|---|---|---|---|---|
| `MWRR cumulative` | Cumulative money-weighted return by day | `history[i].mwrr_cumulative = (1 + history[i].mwrr_annualized)^(days_from_period_start/365) - 1` | `history[*].mwrr_cumulative` | Frontend plots `Number(mwrr_cumulative) × 100`. If backend nulls unreliable series, this line disappears entirely. |
| `TWRR` | Cumulative time-weighted return by day | Same geometric-linking formula as Returns card, but evaluated cumulatively at each snapshot | `history[*].twrr` | Frontend plots `× 100`. First visible point forced to `0`. |
| `ROI` | Simple ROI by day | For each snapshot `t`: `NetInvested_t = max(0, -Σ CF_i<=t)` using period-rebased cash flows; `ROI_t = (NAV_t - NetInvested_t) / NetInvested_t` | `history[*].roi` via `calculate_simple_roi_series()` | Frontend plots `× 100`. First visible point forced to `0`. |
| Series filtering | Whether a % line is rendered at all | Frontend keeps only series where at least one point is non-null | Client-side `pctSeries` | Most relevant for MWRR when backend marks history MWRR unreliable. |

**MWRR reliability check:**
- `get_report()` compares `summary.mwrr_cumulative_percent` vs last history `mwrr_cumulative`.
- If divergence exceeds tolerance (`max(0.5pp, 5% of summary value)`), it retries with cold-start.
- If still bad, backend nulls all history MWRR points and appends a data-quality issue.
- Summary-card MWRR numbers can still exist even when GrowthChart’s MWRR line disappears.

---

## Allocation panel

Source path:
- Frontend: `frontend/src/routes/(app)/dashboard/+page.svelte`
- Current view: `summary.allocation_by_type`, `summary.allocation_by_sector`, `summary.allocation_by_geography`
- History view: `allocation_history.type|sector|geography`
- Backend builders: `DerivedViewsBuilder.build_allocation_current()` and `DerivedViewsBuilder.build_allocation_history()`

**Important:** `loadAllocationHistory()` on the dashboard does **not** call a separate backend endpoint. It only marks a cache key. Dashboard data already came from unified `/portfolio/report`.

## Current Type tab

| Name shown in UI | What it represents | Exact formula / computation | Source | Notes / caveats |
|---|---|---|---|---|
| Pie slice `%` | End-of-range allocation by asset type | For each positive-qty asset with engine market value `mv_asset`: `by_type[asset_type] += mv_asset`; after asset loop: `by_type['Liquidity'] += cash_value + in_transit_cash_value`; then `AllocationItem.value = bucket_amount / Σ bucket_amount × 100` | `summary.allocation_by_type[*].value` | Type allocation includes a cash-like `Liquidity` bucket. |
| Pie tooltip amount | Absolute end-of-range amount behind slice | `AllocationItem.amount = bucket_amount` from formula above | `summary.allocation_by_type[*].amount` | Displayed in target currency. |
| Slice presence | Whether a slice exists in frontend data | Frontend `toAllocEntries()` filters out `value <= 0` | Client-side | Zero/negative slices are removed before charting. |

## Current Sector tab

| Name shown in UI | What it represents | Exact formula / computation | Source | Notes / caveats |
|---|---|---|---|---|
| Pie slice `%` | End-of-range allocation by sector | For each asset with market value `mv_asset`, if metadata has `sector_area.distribution = {sector: weight}` then `by_sector[sector] += mv_asset × weight`; if missing/empty, `by_sector['Unknown'] += mv_asset`; after asset loop: `by_sector['Liquidity'] += cash_value + in_transit_cash_value`; then `AllocationItem.value = bucket_amount / Σ bucket_amount × 100` | `summary.allocation_by_sector[*].value` | Sector allocation includes `Liquidity`. Weights come from asset-classification metadata, not transaction history. |
| Pie tooltip amount | Absolute amount per sector | `AllocationItem.amount = bucket_amount` | `summary.allocation_by_sector[*].amount` | Target currency. |

## Current Geo tab

| Name shown in UI | What it represents | Exact formula / computation | Source | Notes / caveats |
|---|---|---|---|---|
| Country weight on map | End-of-range geography allocation weight | For each asset with market value `mv_asset`, if metadata has `geographic_area.distribution = {country: weight}` then `by_geo[bucket] += mv_asset × weight`, where backend remaps provider `Other` → `Unknown`; if missing/empty, `by_geo['Unknown'] += mv_asset`; then `AllocationItem.value = bucket_amount / Σ bucket_amount × 100`. Frontend converts this to `allocationByGeoMap[country] = value / 100`. `GeographyMap` then converts back to chart value `% = weight × 100`. | `summary.allocation_by_geography[*].value` → `allocationByGeoMap` → `GeographyMap.chartData.value` | Geo allocation does **not** add a cash/liquidity bucket. It is asset geography only. |
| Country amount in labels / tooltip | Absolute end-of-range amount for that country bucket | `allocationByGeoAmounts[country] = AllocationItem.amount`; map label/tooltip displays it with currency formatter | `summary.allocation_by_geography[*].amount` | Only positive amounts kept. |
| `Unknown / unclassified` footnote | Portion of geography allocation not mappable to concrete countries | Frontend: `geoUnknownPercent = Unknown.value + Other.value` | Client-side from `summary.allocation_by_geography` | Backend already merges `Other` into `Unknown`; frontend still sums both defensively. Map omits these from country shading and shows them as note text instead. |
| Map color scale | Relative color intensity, not a financial metric by itself | `visualMap.max = max(displayed_country_percent)` | Client-side `GeographyMap` | Colors are relative to current dataset, not fixed across date ranges. |

## History view

| Name shown in UI | What it represents | Exact formula / computation | Source | Notes / caveats |
|---|---|---|---|---|
| Stacked area layer `%` | Allocation weight of a category over time | Backend iterates daily states `s` with `s.date >= date_from`; for selected dimension, gets `d = s.by_type / by_sector / by_geography`; each component gets `value = amount / Σ amount × 100` and `amount = bucket_amount`; frontend plots `Number(component.value)` on a 100% stacked area chart | `allocation_history.{type|sector|geography}[].components[]` | Same bucket construction rules as current allocation. Type/sector histories include `Liquidity`; geography history does not. |
| Tooltip percentages | Same per-day component weights | Directly from `components[].value` | `allocation_history.*.components[].value` | Tooltip shows percentages; absolute `amount` is present in payload but not plotted as Y-axis. |
| Data loading path | Where the chart comes from | `allocationHistoryData` just selects `allocation_history.type|sector|geography` already loaded by `/portfolio/report` | Frontend `allocationHistoryData` / `loadAllocationHistory()` | `AllocationHistoryChart.svelte` comment mentioning direct `/allocation-history` is outdated for dashboard usage. |

---

## Positions panel

Source files:
- `frontend/src/lib/components/dashboard/PositionsPanel.svelte`
- `frontend/src/lib/components/dashboard/ExposureTable.svelte`
- `frontend/src/lib/components/dashboard/ContributionTable.svelte`
- `frontend/src/lib/components/dashboard/ExposureTreemap.svelte`
- `frontend/src/lib/components/dashboard/ContributionTreemap.svelte`
- Backend sources:
  - `summary.holdings` from `PortfolioService.get_summary()`
  - `positions_contribution` from `PortfolioService.get_positions_contribution()`

## View/mode matrix

| Semantic mode | Visual mode | Open/Closed filter | Component actually rendered | Data source |
|---|---|---|---|---|
| Exposure | Table | Open | `ExposureTable` | `summary.holdings` merged with matching `positions_contribution` row for realized/costs |
| Exposure | Table | Closed | `ExposureTable` closed branch | `positions_contribution.positions.filter(is_fully_sold)` |
| Exposure | Map | Open | `ExposureTreemap` | `summary.holdings` |
| Exposure | Map | Closed | **`ContributionTreemap`** (special switch) | `positions_contribution.positions.filter(is_fully_sold)` |
| Contribution | Table | Open | `ContributionTable` | `positions_contribution.positions.filter(!is_fully_sold)` |
| Contribution | Table | Closed | `ContributionTable` | `positions_contribution.positions.filter(is_fully_sold)` |
| Contribution | Map | Open | `ContributionTreemap` | filtered contribution positions |
| Contribution | Map | Closed | `ContributionTreemap` | filtered contribution positions |

## Backend period-attribution formulas (`get_positions_contribution`)

These formulas were already verified earlier and are the backend truth for Closed Exposure + all Contribution views.

For each `(broker, asset)` with period relevance:

- `qty_at_start = Σ signed quantity of BUY/SELL with tx.date <= date_from`
- `qty_at_end = Σ signed quantity of BUY/SELL with tx.date <= date_to`
- `is_fully_sold = (qty_at_end <= 0)`
- `mv_start = qty_at_start × price_at_date_from`, backward-filled to latest price on or before `date_from`, then converted to base at `date_from`
- `cb_start = qty_at_start × WAC_at_date_from`, converted to base at `date_from`
- `ug_start = mv_start - cb_start` if `qty_at_start > 0`
- `mv_end = qty_at_end × price_at_date_to`, backward-filled to latest price on or before `date_to`, converted to base at `date_to`
- `cb_end = qty_at_end × WAC_at_date_to`, converted to base at `date_to`
- `ug_end = mv_end - cb_end` if `qty_at_end > 0`
- `unrealized_delta = (ug_end or 0) - (ug_start or 0)`
- `realized = Σ(sell_proceeds_base - sell_qty × WAC_before_sell_base)` over SELLs with `date_from < tx.date <= date_to`
- `income = Σ abs(amount_base)` for `DIVIDEND`/`INTEREST` with same date filter
- `fees = Σ abs(amount_base)` for `FEE`/`TAX` with same date filter
- `period_pnl = unrealized_delta + realized + income - fees`
- `period_pnl_percent = period_pnl / abs(start_value)`, where `start_value = mv_start`, falling back to `mv_end` if the position did not exist at period start

**Key identity for fully sold positions (already verified correct):**

If a position is fully sold during the period with no intervening buys,

- `period_pnl = sell_proceeds - mv_start`

So Closed/Contribution period attribution measures **change from start-of-period value to sale**, not lifetime realized gain vs original purchase cost.

Positions are excluded entirely if they were already closed before the selected period and have no relevant activity/result in the period.

Unallocated broker-level income/fees still exist in backend response, but are **not rendered anywhere** in dashboard UI.

## Exposure / Table / OPEN

**Very important time-basis caveat:** this mode is driven by `summary.holdings`, and that holdings loop uses:
- `today = date.today()`
- all-time `net_qty`
- latest price ever via `_get_latest_price()` (no `date_to` bound)
- yesterday vs today for `price_change_1d`

So OPEN Exposure rows are effectively **current/today holdings**, not end-of-range holdings.

| Name shown in UI | What it represents | Exact formula / computation | Source | Notes / caveats |
|---|---|---|---|---|
| `Asset` | Asset identity | Name/icon only | `holding.asset_name`, asset icon lookup | No numeric formula. |
| `Value` | Current holding value from holdings loop | `holding.current_value = compute_holding_value(net_qty, current_price, quote_base_quantity) × share`, where `net_qty = Σ BUY/SELL quantities over all time`; `current_price` comes from latest price ever, converted to base at `price_date`; if no market price but WAC convertible, fallback `current_value = cost_basis` | `summary.holdings[*].current_value` from `PortfolioService.get_summary()` | **Not date-range-aware.** Can differ from engine `summary.market_value`. |
| `Weight %` | Row value as % of engine NAV | `holding.nav_weight_percent = holding.current_value / summary.net_worth.amount × 100` | `summary.holdings[*].nav_weight_percent` | Backend already stores 0–100 value. Because numerator is today/current holdings value and denominator is engine NAV at selected end date, weights can be non-reconciling for historical `date_to`. |
| `Δ1D %` | Current one-day price change | `holding.price_change_1d = (current_price_base - prev_price_base) / prev_price_base`, where `prev_price_base` is latest price on or before `yesterday` converted at `yesterday` FX | `summary.holdings[*].price_change_1d` | Current/today-based, not date-range-aware. Frontend multiplies by 100 for display. |
| `Δ1D` | Current one-day absolute change in row value | Client-side: `dayChangeAbs = currentValue - currentValue / (1 + price_change_1d)` | `ExposureTable.computeDayChangeAbs()` | Pure frontend derivation. Not a backend field. |
| `Unrealized P&L` | Current lifetime unrealized gain/loss on the holding | `holding.gain_loss = holding.current_value - cost_basis`, where `cost_basis = WAC_today_base × net_qty × share` | `summary.holdings[*].gain_loss` | Lifetime/current metric. Not period-scoped. If WAC fallback value is used, this can be `0`. |
| `Realized` | Period realized result merged from contribution row | Current code: `realized_display = period_realized_gain_loss + period_income` | Client-side `ExposureTable.getRealizedAmount()` from matching `positions_contribution` row | **Code adds income here.** Header/tooltip still imply realized sales only. Period-scoped, unlike value/weight/unrealized columns. |
| `Costs` | Period fees/taxes merged from contribution row | `costs_display = period_fees_taxes`, then UI shows `-abs(costs)` in red | Client-side from matching `positions_contribution` row | Period-scoped. Backend value is positive magnitude; UI negates for display. |
| `Broker` | Broker identity | Badge only | `holding.broker_*` | No numeric formula. |

## Exposure / Table / CLOSED

This mode does **not** use `summary.holdings`. It uses contribution rows filtered to `is_fully_sold`.

| Name shown in UI | What it represents | Exact formula / computation | Source | Notes / caveats |
|---|---|---|---|---|
| `Asset` | Asset identity | Name/icon only | `positions_contribution.positions[*]` | No numeric formula. |
| `Realized` | Period realized-like inflow shown in this table | Current code: `realized_display = period_realized_gain_loss + period_income` | Client-side `ExposureTable.getRealizedAmount()` | Again, code includes income even though tooltip says realized sales. |
| `Costs` | Period fees/taxes for the closed position | `costs_display = period_fees_taxes`, rendered as negative | `position.period_fees_taxes` | Period-scoped. |
| `Period P&L` | Total period attribution for the closed position | `period_pnl = unrealized_delta + realized + income - fees` | `position.period_pnl` | For fully sold positions, see key identity above: often simplifies to `sell_proceeds - mv_start`. |
| `Broker` | Broker identity | Badge only | `position.broker_*` | No numeric formula. |

## Contribution / Table

| Name shown in UI | What it represents | Exact formula / computation | Source | Notes / caveats |
|---|---|---|---|---|
| `Asset` | Asset identity | Name/icon only | `positions_contribution.positions[*]` | No numeric formula. |
| `Period P&L` | Total period attribution for that position | `period_pnl = unrealized_delta + realized + income - fees` | `position.period_pnl` | Same formula as backend contribution service. Sorted by `abs(period_pnl)` descending. |
| `Period P&L %` | Period return relative to start-of-period value | Frontend displays `position.period_pnl_percent × 100` | `position.period_pnl_percent` | Backend ratio denominator is `abs(start_value)` with fallback to `mv_end` if position did not exist at period start. |
| `Broker` | Broker identity | Badge only | `position.broker_*` | No numeric formula. |

**Set membership note:**
- Contribution table is filtered by same Open/Closed toggle as Exposure:
  - open = `!is_fully_sold`
  - closed = `is_fully_sold`
- No synthetic “Unallocated” rows are shown.

## Exposure / Map

| Name shown in UI | What it represents | Exact formula / computation | Source | Notes / caveats |
|---|---|---|---|---|
| Treemap box area | Current holding size | `box.value = holding.current_value` | `summary.holdings[*].current_value` | Same caveats as OPEN Exposure table: current/today holdings loop, not end-of-range engine snapshot. |
| Treemap hierarchy | Grouping only | Broker → Asset Type → Asset | Client-side `ExposureTreemap.buildTreeData()` | No numeric computation beyond grouping. |
| Treemap color | Current unrealized return % on the holding | Color function uses `holding.gain_loss_percent` | `summary.holdings[*].gain_loss_percent` | Positive → green, negative → red. Intensity saturates at `|gain_loss_percent| = 0.50` (50pp). |
| Tooltip `Value` | Current holding value | `holding.current_value` | same as above | Not engine `summary.market_value`. |
| Tooltip `NAV weight` | Row weight vs engine NAV | `holding.nav_weight_percent` | same as above | Same mismatch caveat as open table. |
| Tooltip `Unrealized P&L` | Current lifetime unrealized amount | `holding.gain_loss` | same as above | Lifetime/current, not period-scoped. |

**Special CLOSED behavior:**
- Exposure + Map + Closed does **not** render ExposureTreemap.
- It switches to `ContributionTreemap` over `is_fully_sold` positions.

## Contribution / Map

| Name shown in UI | What it represents | Exact formula / computation | Source | Notes / caveats |
|---|---|---|---|---|
| Gains panel height | Relative gross positive contribution vs gross negative contribution | `scaleMax = max(grossGains, grossLosses)`; `gainsHeight = max((grossGains / scaleMax) × totalHeight × 0.85, grossGains > 0 ? 60 : 0)` | Client-side `ContributionTreemap` | `grossGains` is recomputed client-side from the **currently filtered** positions, not taken from backend totals. |
| Losses panel height | Relative gross losses vs gains | `lossesHeight = max((grossLosses / scaleMax) × totalHeight × 0.85, grossLosses > 0 ? 60 : 0)` | Client-side | Same current-filter rule. |
| Asset box area | Magnitude of period contribution | `box.value = abs(position.period_pnl)` | `position.period_pnl` | Gains and losses use separate treemaps, so sign is encoded by which chart you are in. |
| Box color | Sign only | Gains chart fixed green; losses chart fixed red | Client-side render path | Unlike Exposure map, color does **not** encode magnitude. |
| Tooltip `Period P&L` | Period attribution amount | `position.period_pnl` | same as above | Displayed with sign. |
| Tooltip `%` | Period return % | Frontend shows `position.period_pnl_percent × 100` | `position.period_pnl_percent` | Ratio in backend, percent in UI. |
| Hierarchy | Grouping only | Broker → Asset Type → Asset | Client-side `buildTreeData()` | No extra math. |

---

## Recent Transactions panel

Source files:
- `frontend/src/lib/components/dashboard/RecentTransactionsPanel.svelte`
- `frontend/src/lib/components/transactions/TransactionsTable.svelte`
- Shared row type: `frontend/src/lib/components/transactions/types.ts`

**Important scope note:** this panel does **not** use dashboard date range. It only uses:
- `limit`
- optional broker filter (`brokerIds`)

### Row selection logic

This panel is near-raw recent data, but not literally “first N rows from endpoint”:

1. For each broker scope, frontend requests transactions with `limit = dashboard_limit × 3`.
2. It sorts locally by:
   - `date DESC`
   - then `id DESC`
3. It removes rows whose `id` appears as another row’s `related_transaction_id` (so dashboard keeps only the main/non-partner row of linked pairs such as transfers / FX conversions).
4. It slices first `limit` rows after that cleanup.

### Visible columns in compact/dashboard mode

`RecentTransactionsPanel` passes `hiddenColumns = ['links', 'tags', 'id', 'description']` to `TransactionsTable`, so visible columns are:
- `Date`
- `Type`
- `Quantity`
- `Cash`
- `Asset`
- `Broker`

| Name shown in UI | What it represents | Exact formula / computation | Source | Notes / caveats |
|---|---|---|---|---|
| `Date` | Stored transaction date | raw `tx.date` | `TXReadItem.date` | No derived math. |
| `Type` | Stored transaction type | raw `tx.type`, rendered as icon + label/tooltip | `TXReadItem.type` | No derived math. |
| `Quantity` | Stored signed quantity | raw `tx.quantity` formatted by `formatTxQuantity()` | `TXReadItem.quantity` | No portfolio calculation; formatting only. |
| `Cash` | Stored signed cash amount in transaction currency | raw `tx.cash.amount` with raw `tx.cash.code` | `TXReadItem.cash` | Not converted into dashboard display currency. |
| `Asset` | Linked asset identity | raw `tx.asset_id` resolved to display name/icon | `TXReadItem.asset_id` + asset store | No derived math. |
| `Broker` | Broker identity | raw `tx.broker_id` resolved to badge | `TXReadItem.broker_id` + broker store | No derived math. |

So: **no financial formulas here beyond local sorting/dedup/filtering of recent rows and formatting of stored values.**

---

## Data quality banner (when visible)

This is not a portfolio-math widget, but it does show counts on the dashboard.

Source path:
- Dashboard passes `summary.data_quality.issues` into `DataQualityBanner`
- Backend produces issues in `PortfolioService.get_summary()` / `DerivedViewsBuilder.build_data_quality_report()`
- Dashboard may append an extra `MWRR_SERIES_UNRELIABLE` issue in `get_report()`

| Number shown in UI | Exact computation | Source | Notes |
|---|---|---|---|
| Header error count | `issues.filter(i => i.severity === 'error').length` | Client-side `DataQualityBanner` | If zero, omitted from header text. |
| Header warning count | `issues.filter(i => i.severity === 'warning').length` | Client-side | If zero, omitted from header text. |
| `+N` more issues | `sortedIssues.length - 3` | Client-side | Only when more than 3 issues exist in grouped mode. |
| `+N` more asset names | `(affected_asset_names.length - shown_count)` | Client-side | Pure list-overflow counter. |
| `+N` more FX pairs | `(affected_fx_pairs.length - shown_count)` | Client-side | Pure list-overflow counter. |
| Dates/counts inside issue text | Whatever backend placed into `issue.message_params` | Backend issue builder | Example: NAV incomplete uses count and date range. |

---

## High-value reconciliation caveats

These are the main reasons two dashboard numbers can both be “correct according to code” yet not reconcile naively.

1. **OPEN Exposure widgets are current-holdings widgets, not historical end-date widgets.**
   - They come from `summary.holdings`, built with `today`, latest price ever, all-time net quantity, and today/yesterday 1D change.
   - This can diverge from engine-based KPI/Allocation/Growth widgets when `date_to` is in the past.

2. **OPEN Exposure mixes current and period-scoped columns in the same row.**
   - Current/today: Value, Weight, Δ1D %, Δ1D, Unrealized P&L.
   - Period-scoped: Realized, Costs.

3. **OPEN Exposure “Realized” currently includes income.**
   - Code path is `period_realized_gain_loss + period_income`.

4. **Net Worth sub-bars do not fully span the hero NAV concept.**
   - Hero `Net Worth` includes in-transit market value.
   - Visible bars show `market_value`, `open_cost_basis` (mislabeled Book Value), `cash_total`, `net_deposited_capital`.
   - No separate row is shown for `in_transit_market_value`.

5. **The “Book Value” KPI row is actually `open_cost_basis`, not `book_value`.**
   - And its start marker uses `period_book_value_start` only as proxy.

6. **Period P&L KPI breakdown can have hidden residual.**
   - Backend computes `period_other_result` but UI does not show it.

7. **Allocation and Growth are engine-based; Exposure OPEN is not.**
   - Allocation uses engine daily states and classification metadata.
   - Growth uses engine daily states + ROI algorithms.
   - Exposure OPEN uses separate holdings loop logic.

8. **Recent Transactions ignores date range.**
   - It is broker-filtered only.
