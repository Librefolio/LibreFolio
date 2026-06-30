# Asset-Level Contribution Gap Analysis

> Generated: 2026-06-26  
> Scope: read-only engine analysis — no code changes  
> Corrects the previous `report_dashboard_bottom_widgets_analysis.md` which was too pessimistic  
> Files analyzed: `portfolio_engine.py` (1511 lines), `portfolio_service.py` (1502 lines)

---

## 1. Executive Summary

### Conclusion

**The previous report was too pessimistic.** Phase B (Contributo widget) does NOT require a "new sub-engine". The engine already computes the necessary data transiently; the work is largely an **accumulator refactor** + **targeted 2-date lookup** using existing pre-loaded data structures.

### Real gap estimate

| Component | Previous estimate | Revised estimate |
|-----------|------------------|-----------------|
| unrealized_delta per asset | New engine C | Targeted 2-date lookup B |
| realized_gain_loss per asset | New algorithm C | Dict accumulator in existing loop B |
| income per asset | Moderate work B/C | Trivial: asset_id already on tx B |
| fees_taxes per asset | Blocked D | Mostly unallocated (no asset_id); easy if asset_id present B/D |
| period_pnl (total) | New service C | Sum of above B components B |
| period_pnl_percent | Complex C | Start-position value lookup B |

### Was the previous report correct?

- Correct: the data is NOT in any current API response. No endpoint exposes per-asset contribution.
- Too pessimistic: it implied a new computation algorithm was needed. The data already exists in engine data structures; it's mostly an exposure/accumulation problem.

### Recommendation

Phase B can be implemented as an **extension of the existing `get_summary()` loop** in `portfolio_service.py`, adding:
1. Per-position accumulators for realized, income, fees
2. A targeted start/end date unrealized GL computation using pre-loaded price_map + wac_series (NO full engine rerun)
3. A new `get_positions_contribution()` method + new DTO + new endpoint

Estimated backend effort: **2–3 days** for a clean implementation, not 1–2 weeks.

---

## 2. Existing Engine Capabilities

### 2.1 Asset price by date

**`DailyStateBuilder._price_on_date(sorted_prices, query_date)`** (engine line ~653):
- Backward-fill: returns `(close, currency, actual_date)` for latest price ≤ query_date
- Pre-loaded as `price_map: dict[asset_id, list[tuple[date_type, Decimal, str]]]`
- Supports any date in the loaded range (loaded up to `actual_to`)
- **Price is NOT per-broker** — an asset has one price regardless of broker

**`PortfolioCalculationEngine.calculate()`** pre-loads prices for all held assets via bulk query:
```python
# Engine line 1336-1347
price_stmt = select(PriceHistory).where(
    PriceHistory.asset_id.in_(held_asset_ids),
    PriceHistory.date <= actual_to
)
price_map[ph.asset_id] = [(ph.date, ph.close, ph.currency), ...]
```

**FX handling**: `fx_rate_map: dict[(from_ccy, to_ccy, date), Decimal]` pre-loaded for every day in range. All price queries can be FX-converted using existing rate map.

**Verdict**: ✅ Reusable single function for any (asset_id, date). Supports target_currency. Supports broker scope (prices are asset-level). Supports date range. No new work needed here.

### 2.2 Quantity by date per asset/broker

**`DailyStateBuilder.build()`** (engine line 442-481):
```python
# Quantity ledger — maintained per (asset_id, broker_id) per day
cumulative_qty: dict[tuple[int, int], Decimal] = defaultdict(...)

for ctxn in classified_txs:
    if tx.quantity and tx.asset_id:
        key = (tx.asset_id, tx.broker_id)
        qty_deltas[tx.date][key] += tx.quantity * share

# In daily loop:
for key, delta in day_qty.items():
    cumulative_qty[key] += delta
```

The key insight: **`cumulative_qty[(asset_id, broker_id)]` IS maintained per position throughout the loop** but then used as:
```python
for (asset_id, _broker_id), qty in cumulative_qty.items():  # broker_id discarded!
    mv = _market_value_for(asset_id, qty, current)
    market_value += mv  # summed to portfolio total
```

The `_broker_id` is intentionally ignored because prices are the same across brokers for the same asset. But the (broker_id, asset_id) dimension IS maintained — it's just not propagated to `DailyPortfolioState`.

**Verdict**: ✅ Per-(asset_id, broker_id) quantities are computed at every date transiently. The broker_id is NOT lost; it exists in `cumulative_qty` as a key throughout the loop. No new quantity tracking needed.

### 2.3 Market value by date

**`DailyStateBuilder._market_value_for(asset_id, qty, dt)`** (engine line ~683):
- Three paths: MARKET_PRICE (backward-fill), TRANSACTION_IMPLIED (WAC proxy), MISSING
- Returns `(value_in_target_ccy, price_found, is_stale, missing_fx_pair, is_implied)`
- For each (asset_id, broker_id) in `cumulative_qty`, an individual `mv` is computed
- BUT: only `market_value += mv` (portfolio sum) is stored in `DailyPortfolioState`

Per-position market_value IS computed transiently. To expose it, the `DailyPortfolioState` would need a new field, OR a targeted one-time computation for the 2 dates of interest (start, end).

**Verdict**: ✅ Per-position market_value is computable from existing data. No new algorithms needed.

### 2.4 WAC / cost basis by date

**Pre-loaded `wac_series: dict[tuple[int, int], list[tuple[date_type, Decimal, str]]]`** (engine line 1360-1378):
```python
for asset_id in held_asset_ids:
    for broker_id in scope_broker_ids:
        wac_result = await compute_wac_iterative(...)
        # Builds series of (date, running_wac, currency) from qualifying txs
        wac_series[(asset_id, broker_id)] = sorted(series)
```

**`DailyStateBuilder._wac_on_date(sorted_wac, query_date)`** (engine line ~668):
- Forward-fill: latest WAC ≤ query_date
- Used in `_compute_open_cost_basis()` to get WAC × qty per position

For any date in range:
```python
wac_val, wac_ccy = _wac_on_date(wac_series[(asset_id, broker_id)], date)
ocb_position = wac_val * qty  # in wac_ccy
# FX convert to target_currency using fx_rate_map[(wac_ccy, target_ccy, date)]
```

**Verdict**: ✅ WAC per-position available at any date via pre-loaded series. No new computation needed.

### 2.5 Existing history/report calculation loop

**Two computation paths exist in `portfolio_service.py`:**

#### Path A: Engine-driven (DailyPortfolioState)
Used by `get_summary()` → `PortfolioCalculationEngine.calculate()` → `DerivedViewsBuilder`
- Computes full daily time series (all dates from first tx to today)
- Portfolio-level aggregates only (market_value, NAV, unrealized_gl, etc.)
- Per-position data computed transiently but not stored

#### Path B: Legacy per-asset loop in `get_summary()` (lines 612-840)
- Still runs AFTER the engine, per-broker/asset
- Purpose: compute PortfolioHolding[], BrokerBreakdown[], realized SELL, income, fees
- Uses `compute_wac_iterative()` per (broker_id, asset_id) → one DB+FX call each
- Per-(broker_id, asset_id) realized, income, fees are computed but ONLY accumulated to portfolio-level totals (`_realized_accum`, `_income_accum`, `_fees_taxes_accum`)

**The realized P&L loop already IS per-asset (lines 692-733):**
```python
for asset_id, asset_txns in txns_by_asset.items():  # ← per-asset iteration
    for tx in asset_txns:
        if tx.type != TransactionType.SELL:
            continue
        ...
        cost_sold = sell_qty * wac_at_sell_base
        _realized_accum += (sell_proceeds - cost_sold) * share  # ← just needs dict!
```

**The income loop is in the outer broker loop (lines 640-680):**
```python
for tx in broker_txns:  # ← all transactions
    ...
    if in_period and tx.type in _INCOME_TYPES:   # DIVIDEND, INTEREST
        _income_accum += abs(amount_base_signed) * share  # ← tx.asset_id available!
```

DIVIDEND/INTEREST transactions have `asset_id: Optional[int]` on the Transaction model. In practice, DIVIDEND always has asset_id. INTEREST may or may not (broker-level interest vs asset-linked interest).

---

## 3. Component Gap Analysis

### 3.1 Unrealized delta per asset

**Target**: `asset_unrealized_gl(end) - asset_unrealized_gl(start)` where:
```
asset_unrealized_gl(date, broker, asset) = mv(asset, qty, date) - wac_per_unit(broker, asset, date) × qty(date)
```

**What already exists:**
- `price_map[asset_id]` + `_price_on_date()` → price at any date ✅
- `wac_series[(asset_id, broker_id)]` + `_wac_on_date()` → WAC at any date ✅
- `cumulative_qty[(asset_id, broker_id)]` at end date from `DailyStateBuilder` ✅
- `fx_rate_map[(ccy, target_ccy, date)]` for any date in range ✅

**What doesn't exist yet:**
- `qty_at_start` per (asset_id, broker_id) is NOT directly stored — must be reconstructed by summing all qty_deltas up to date_from
- `DailyPortfolioState` does NOT store per-position unrealized_gl

**Approach (without full engine rerun):**
1. Build a lightweight `qty_at_date` function: sum all transaction quantities for (broker_id, asset_id) up to date_from using pre-loaded `classified_txs`
2. For start: `qty_start = sum(tx.qty for tx in classified_txs if tx.broker_id == b and tx.asset_id == a and tx.date <= date_from)`
3. For end: `qty_end = sum(same but tx.date <= date_to)` — same as holdings quantity
4. Compute `ug_start = price(asset, date_from) × qty_start - wac(broker, asset, date_from) × qty_start`
5. Compute `ug_end = price(asset, date_to) × qty_end - wac(broker, asset, date_to) × qty_end`
6. `unrealized_delta = ug_end - ug_start`

**Edge cases for unrealized_delta:**
- **BUY during period**: qty_start < qty_end. ug_start uses smaller qty. Formula is still correct (unrealized_delta = change in position value minus change in cost basis).
- **SELL partial**: qty_end < qty_start. ug_end uses reduced qty. Correct.
- **SELL total** (qty_end = 0): ug_end = 0. Delta = 0 - ug_start = - ug_start. This is fine.
- **New position (bought during period)**: qty_start = 0, ug_start = 0. Delta = ug_end. Correct.
- **No price at start/end**: ug = None → unrealized_delta = None → show "—" with data quality flag.
- **Manual/crowdfund**: price fallback to WAC (TRANSACTION_IMPLIED path). ug = 0 always (WAC = price). unrealized_delta always 0 for manual assets. Acceptable — just label accordingly.

**Classification: B** — data already exists in pre-loaded structures. Needs a lightweight qty-at-date function + targeted 2-point UGL computation. NO full engine rerun.

### 3.2 Realized gain/loss per asset

**Current code (portfolio_service.py lines 692-733):**

```python
for asset_id, asset_txns in txns_by_asset.items():
    for tx in asset_txns:
        if tx.type != TransactionType.SELL: continue
        if not in_period: continue
        # Computes WAC at sell date via compute_wac_iterative()
        cost_sold = sell_qty * wac_at_sell_base
        _realized_accum += (sell_proceeds - cost_sold) * share
        #                                                ↑ just add a dict here:
        # per_realized[(broker_id, asset_id)] += (sell_proceeds - cost_sold) * share
```

This loop already:
- Iterates per (broker_id, asset_id) ✅
- Filters by period ✅
- Computes realized using `compute_wac_iterative(excluded_tx_ids=[tx.id])` ✅
- Converts to base/target currency ✅

**Change needed**: 2 lines — initialize `per_realized: dict[tuple[int,int], Decimal] = defaultdict(Decimal)` and change `_realized_accum +=` to also write to the dict.

**Note on `compute_wac_iterative` performance**: Each SELL requires one async call to `compute_wac_iterative()` (DB query + WAC computation). This is already the bottleneck in `get_summary()`. For the Contributo endpoint, same cost. For portfolios with many SELLs in a period, this could be slow — but it's the same algorithm as today.

**Classification: B** — trivial accumulator change. No new algorithm.

### 3.3 Income per asset

**Current code (portfolio_service.py lines 629-680):**
```python
_INCOME_TYPES = {TransactionType.DIVIDEND, TransactionType.INTEREST}

for tx in broker_txns:
    if in_period and tx.type in _INCOME_TYPES:
        _income_accum += abs(amount_base_signed) * share
        # ← add:
        # if tx.asset_id:
        #     per_income[(broker_id, tx.asset_id)] += abs(amount_base_signed) * share
        # else:
        #     per_unallocated_income[broker_id] += abs(amount_base_signed) * share
```

**DIVIDEND**: `asset_id` is **required** by transaction schema (`schemas/transactions.py:221-230`). Always populated. ✅

**INTEREST**: `asset_id` is **optional** by default (`schemas/transactions.py:232-233`), BUT becomes required when `asset_event_id` is set (`:256-269`). Bond coupon INTEREST via asset event → has asset_id. Crowdfund INTEREST (e.g., Recrowd) → has asset_id linked to the loan asset. Broker cash interest (no event) → no asset_id.

**Unallocated income** (no asset_id): goes to a "Portfolio/Unallocated" row in Contributo view. Not a blocking issue.

**Classification: B** — 3-line change. No new algorithm.

### 3.4 Fees/taxes per asset

**FEE transactions**: Commissions on trades — may or may not have asset_id. In Directa CSV imports, commission records often do NOT have asset_id (they're separate FEE rows). Some brokers link FEE to the associated BUY/SELL, others don't.

**TAX transactions**: Tax withholding — typically linked to a DIVIDEND (may have asset_id) or standalone tax (no asset_id).

**Existing code (portfolio_service.py lines 675-680):**
```python
if in_period and tx.type in _FEE_TAX_TYPES:
    _fees_taxes_accum += abs(amount_base_signed) * share
```

**Change needed:**
```python
if in_period and tx.type in _FEE_TAX_TYPES:
    _fees_taxes_accum += abs(amount_base_signed) * share
    if tx.asset_id:
        per_fees[(broker_id, tx.asset_id)] += abs(amount_base_signed) * share
    else:
        per_unallocated_fees[broker_id] += abs(amount_base_signed) * share
```

**Verdict**: Partially attributable. asset_id is optional on FEE/TAX. Many fees will be unallocated. This is by design — the "Portfolio" row in Contributo view captures unallocated fees. Not a blocker.

**Classification: B for linked fees, D for unlinked fees** (unlinked fees → Portfolio bucket, cannot attribute without euristics).

### 3.5 Assets sold completely during period

**Critical gap confirmed.** In `portfolio_service.get_summary()` (line 746-748):
```python
net_qty = sum(tx.quantity or 0 for tx in asset_txns if tx.type in (BUY, SELL))
if net_qty <= 0:
    continue  # ← SKIPS fully-sold positions!
```

BUT: the realized SELL loop (lines 698-733) runs BEFORE this check. So realized P&L IS computed per (broker_id, asset_id) for fully-sold positions IF we use a dict accumulator. The data is just thrown away at the `continue` before `all_holdings.append()`.

**Fix for Contributo view:**
- Use the `per_realized` dict (from §3.2) to include fully-sold positions
- For unrealized_delta: ug_end = 0 (no position), ug_start = qty_start × (price_start - wac_start). `unrealized_delta = -ug_start`.
- These positions DO NOT appear in PortfolioHolding (they have no current value), but they CAN appear in the Contributo table with P&L = 0 unrealized + realized_gain.

**Verdict**: Real gap in current PortfolioHolding, but solvable in the Contributo endpoint by using a separate accumulation path.

**Classification: B** — needs separate accumulator; fully-sold positions have realized data if we collect it.

### 3.6 FX / target currency effects

All existing computation already handles FX:
- `fx_rate_map[(from_ccy, to_ccy, date)]` pre-loaded for every date in range ✅
- `_convert()` helper available in `DailyStateBuilder` ✅
- `portfolio_service.get_summary()` converts all amounts to `base_currency` before accumulating ✅
- `compute_wac_iterative()` returns WAC in asset currency → service converts to base_currency

For the Contributo endpoint, the same FX handling can be reused. No new FX logic needed.

**Classification: A** — already implemented.

---

## 4. Can Current Daily Engine Produce This?

### Why the daily engine loop isn't the right path

The `DailyStateBuilder.build()` runs for EVERY calendar day from first tx to today. For a portfolio with 5 years of history, this is 1825 daily iterations × N assets × M brokers. It's designed for full time series, not for "give me start + end snapshots."

For per-asset contribution, we only need **2 date snapshots** (period_start and period_end), not a daily series. Running the full daily builder just to get 2 snapshots would be wasteful.

### The right approach: targeted 2-snapshot computation

The engine pre-loads ALL data (prices, WAC, FX) needed for the full series. For the Contributo endpoint, we can:

1. **Reuse the engine's pre-loaded data structures** (price_map, wac_series, fx_rate_map) without re-running the full daily loop
2. **Compute qty_at_date(broker_id, asset_id, date)** via a simple sum over classified_txs — O(N_txs) single pass
3. **Compute ug_position(broker_id, asset_id, date)** from price + WAC + qty at that date — O(1) per position
4. **Reuse the existing realized SELL loop** in portfolio_service with dict accumulator — no extra computation

### What the daily engine ALREADY computed that can be queried

If `get_report()` has already run the engine (e.g., on the same request), the resulting `daily_states` vector contains, at each date:
- `unrealized_gain_loss` (portfolio total) — can derive asset-level if positions were stored
- `total_pnl` (portfolio total)

However, since per-position is NOT stored in `DailyPortfolioState`, even with the daily states in hand, you cannot derive per-asset contribution from them. The daily states are portfolio aggregates.

### Summary table

| What | Exists in daily engine | Transient in loop | Needs new code |
|------|----------------------|-------------------|---------------|
| qty(broker, asset, date) | ✅ cumulative_qty dict | Yes — discarded at end | No — recompute from txns |
| price(asset, date) | ✅ price_map pre-loaded | Available | No |
| wac(broker, asset, date) | ✅ wac_series pre-loaded | Available | No |
| mv(broker, asset, date) | ✅ computed per position | Summed away | No — recompute from above |
| unrealized_gl(pos, date) | ❌ not in DailyPortfolioState | Derivable | Targeted compute |
| realized(broker, asset, period) | ✅ computed in get_summary() | Accumulated globally | Dict accumulator |
| income(broker, asset, period) | ✅ computed in outer loop | Accumulated globally | Dict accumulator |
| fees(broker, asset, period) | ✅ if asset_id present | Accumulated globally | Dict accumulator |
| pnl(broker, asset, period) | ❌ | Derivable | Sum of above |

---

## 5. Recommended Backend Design

### New method: `get_positions_contribution()`

Add to `PortfolioService` (alongside `get_summary()`, `get_history()`):

```python
async def get_positions_contribution(
    self,
    user_id: int,
    broker_ids: list[int] | None = None,
    date_from: date_type | None = None,
    date_to: date_type | None = None,
    target_currency_override: str | None = None,
) -> list[AssetPeriodContribution]:
```

**Implementation strategy** — reuse get_summary() inner loop, split off as helper:

```python
# Phase 1: Run engine once (reuse if from get_report())
engine_result = await engine.calculate(user_id, broker_ids, ...)
# engine_result.classified_txs, price_map, wac_series, fx_rate_map all pre-loaded

# Phase 2: For each (broker_id, asset_id) pair with any activity in period:

# A) Realized: reuse existing SELL loop with dict accumulator
per_realized: dict[tuple[int,int], Decimal] = defaultdict(Decimal)
# (same loop as lines 698-733, but accumulate per-position)

# B) Income: reuse income loop with dict accumulator  
per_income: dict[tuple[int,int], Decimal] = defaultdict(Decimal)
# (same loop as lines 673-674, add tx.asset_id check)

# C) Fees: reuse fee loop with dict accumulator
per_fees: dict[tuple[int,int], Decimal] = defaultdict(Decimal)
# (same loop as lines 675-680, add tx.asset_id check)

# D) Unrealized delta: targeted 2-snapshot computation
def get_ug_at(broker_id, asset_id, date):
    qty = qty_at_date(broker_id, asset_id, date)  # sum txns up to date
    price = _price_on_date(price_map[asset_id], date)
    wac = _wac_on_date(wac_series[(asset_id, broker_id)], date)
    if any is None: return None
    mv = fx_convert(price × qty, date)
    ocb = fx_convert(wac × qty, date)
    return mv - ocb

per_unrealized_delta = {
    pos: (get_ug_at(*pos, date_to) or 0) - (get_ug_at(*pos, date_from) or 0)
    for pos in all_active_positions
}

# Phase 3: Assemble AssetPeriodContribution[]
```

### Reuse engine data without re-running

The critical optimization: if `get_report()` is the primary API, extend `PortfolioReportQuery`/`PortfolioReportResponse` to optionally include `positions_contribution: list[AssetPeriodContribution]`. This lets a single engine run provide both `summary` + `positions_contribution` without a second compute pass.

### Performance notes

- `compute_wac_iterative()` is called once per SELL in period (already in existing code) — no change
- New qty_at_date() is O(N_txs) per call — trivial
- New 2-snapshot UGL is O(1) per position — trivial
- FX lookups use the pre-loaded dict — O(1) per lookup

---

## 6. DTO / API Proposal

### New Pydantic schema

```python
class AssetPeriodContribution(BaseModel):
    asset_id: int
    asset_name: str
    asset_ticker: Optional[str] = None
    asset_type: str
    broker_id: int
    broker_name: str
    period_unrealized_delta: Optional[SafeDecimal] = None   # None = price missing
    period_realized_gain_loss: Optional[SafeDecimal] = None # None = no SELLs or FX issue
    period_income: Optional[SafeDecimal] = None             # None = no DIVIDEND/INTEREST
    period_fees_taxes: Optional[SafeDecimal] = None         # None = no FEE/TAX linked
    period_pnl: Optional[SafeDecimal] = None                # sum of above (None if all None)
    period_pnl_percent: Optional[SafeDecimal] = None        # period_pnl / |start_cost_basis|
    data_quality_flags: list[str] = []                      # "no_price_start", "no_wac", etc.
    is_fully_sold: bool = False                             # True if qty_end = 0

class UnallocatedContribution(BaseModel):
    """Fees/income not linked to a specific asset."""
    broker_id: int
    broker_name: str
    unallocated_income: Optional[SafeDecimal] = None
    unallocated_fees_taxes: Optional[SafeDecimal] = None
```

### New endpoint

```
POST /api/v1/portfolio/positions-contribution
body: PortfolioContributionQuery (broker_ids, date_range, target_currency)
response: {
    positions: list[AssetPeriodContribution],
    unallocated: list[UnallocatedContribution],
    period_pnl_total: Currency,          # sum check = PortfolioSummary.period_pnl
    gross_gains: SafeDecimal,
    gross_losses: SafeDecimal,
}
```

OR: extend `PortfolioReportQuery` to include an `include_positions_contribution: bool` field (default False), returning the data in a single `/report` call.

---

## 7. Edge Cases

| Scenario | Behavior | Recommendation |
|----------|----------|---------------|
| **BUY during period** (no start position) | qty_start=0, ug_start=0. unrealized_delta = ug_end | Correct — shows gain/loss on new position |
| **SELL partial** | qty changes during period. ug_start = qty_start × (price_start - wac_start) | Correct — delta captures P&L on what was held |
| **SELL total** (qty_end=0) | unrealized_delta = -ug_start (all unrealized flips to 0). realized captures the actual result | Correct — position fully closed; both unrealized reset and realized included |
| **Asset not held at period start but fully sold during** | qty_start=0 (or bought+sold same period). Realized P&L from SELL loop covers it | Include via `per_realized` dict even if not in holdings |
| **No market price at period start** | ug_start = None (MISSING path in `_market_value_for`). unrealized_delta = None | Flag as "no_price_start". Show realized+income-fees only |
| **No market price at period end** | ug_end = None → current holdings show "—" | Same as MISSING_PRICE issue |
| **WAC missing** (no qualifying txs) | wac = None → ug = None | Flag "no_wac". Show income/fees if available |
| **Manual/crowdfund asset** | TRANSACTION_IMPLIED: price = WAC. ug always = 0. unrealized_delta = 0 | Not wrong — just always 0. Label "no market price" |
| **Income without asset_id** (cash interest) | Goes to UnallocatedContribution | Show as "Portfolio" row in Contributo table |
| **Multiple brokers same asset** | Each (broker_id, asset_id) pair is a separate row | Contribution table: two rows for VWCE@Directa + VWCE@IBKR |
| **Zero start value** | period_pnl_percent = None (avoid division by zero) | Use None → show "—" |
| **All gains / no losses** | gross_losses = 0. Treemap shows only GAINS; LOSSES section hidden | Already covered in previous report's edge cases |
| **FX rate missing at start date** | ug_start = None for that position | Flag "no_fx_start". Degrade gracefully |
| **share_percentage != 1** | Already handled — all amounts multiplied by `share` in existing loops | No new work |

---

## 8. Final Classification

| Component | Classification | Evidence | Minimal work |
|-----------|----------------|----------|--------------|
| unrealized_delta per asset | **B** | `price_map`, `wac_series`, `cumulative_qty` all pre-loaded. Need qty_at_date() helper + 2-date UGL compute | ~30 lines of helper code |
| realized_gain_loss per asset | **B** | Lines 698-733 already per-(broker, asset). Need dict accumulator | 2 lines |
| income per asset | **B** | Lines 673-674: tx.asset_id present on DIVIDEND/INTEREST. Need dict + asset_id check | 4 lines |
| fees_taxes per asset | **B/D** | Lines 675-680: asset_id optional. B if present, D if absent → unallocated bucket | 5 lines + unallocated DTO |
| period_pnl per asset | **B** | Sum of above components | 1 line |
| period_pnl_percent | **B** | Need start_position_value = qty_start × price_start (same data as unrealized_delta). Divide period_pnl by abs(start_value or start_cost_basis) | ~5 lines |
| broker_id in PortfolioHolding | **A** | Available in existing service loop (line 785). Just not in DTO | 2 lines (schema + service) |
| Fully-sold position in Contributo | **B** | Realized loop runs before `net_qty <= 0: continue`. Need dict accumulator to not discard | No new algorithm, just accumulate before skip |
| FX conversion | **A** | Already handled in all paths | No work |

### Total revised estimate

| Task | Effort |
|------|--------|
| Add broker_id/broker_name to PortfolioHolding DTO | 30 min |
| New `get_positions_contribution()` method | 1 day |
| New `AssetPeriodContribution` DTO + endpoint | 2 hours |
| `./dev.py api sync` + frontend integration | 1 hour |
| Testing + edge cases | 1 day |
| **Total** | **~2.5 days** |

Previous report said "hard dependency, significant work". Revised: **moderate accumulator work, ~2-3 days, no new algorithm design needed.**

---

## Commands Executed

```bash
# Read engine files directly
view portfolio_engine.py (full 1511 lines in 4 view_range calls)
view portfolio_service.py (lines 1-100, 565-840 for get_summary loop)

# Grep for types and asset_id usage
grep "_HOLDING_TYPES|_CASH_FLOW_TYPES|_INCOME_TYPES|_FEE_TAX" portfolio_service.py
grep "class Transaction|asset_id|FEE|TAX|DIVIDEND|INTEREST" backend/app/db/models.py
```

---

*End of report.*
